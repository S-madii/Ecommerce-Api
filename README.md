# Commerce API

An asynchronous e-commerce backend built with **FastAPI**, **PostgreSQL 16**, **SQLAlchemy 2.0 (`asyncpg`)**, **Redis**, **Celery**, and **Stripe**.

---

## 1. System Overview

```mermaid
flowchart TD
    Client["Client / Frontend"]

    subgraph API ["FastAPI Application (app/)"]
        AuthRouter["/auth (JWT Auth)"]
        CatRouter["/categories (Catalog)"]
        ProdRouter["/products (Filtered / Paginated)"]
        CartRouter["/cart (User Cart Session)"]
        OrderRouter["/orders (Checkout Engine)"]
        PayRouter["/payments (Webhook Listener)"]
    end

    subgraph ServiceLayer ["Service Layer (app/services/)"]
        CartService["CartService<br/>- Active cart session<br/>- Item mutations & subtotals"]
        ProdService["ProductService<br/>- Catalog filtering & search<br/>- Cache-aside & invalidation"]
        OrderService["OrderService<br/>- Decoupled checkout<br/>- Pessimistic locking & compensation"]
        PayService["PaymentService<br/>- Stripe Intent creation<br/>- HMAC webhook verification"]
    end

    subgraph Storage ["Persistence & Messaging"]
        PG[("PostgreSQL 16")]
        Redis[("Redis 7<br/>(Cache & Broker)")]
        Worker["Celery Worker<br/>(app/worker.py)"]
    end

    subgraph External ["Third-Party APIs"]
        Stripe["Stripe API"]
    end

    Client <--> API
    CartRouter --> CartService
    ProdRouter --> ProdService
    OrderRouter --> OrderService
    OrderService --> PayService
    PayRouter --> PayService
    ProdService <--> Redis
    PayRouter -.->|".delay(order_id)"| Redis
    Redis -.-> Worker
    PayService <--> Stripe
    ServiceLayer <--> PG
```

---

## 2. Architecture & Design Patterns

### A. Layered Structure
1. **Presentation Layer (`app/routers/`)**: Route controllers handling HTTP status codes, query/path validation, dependency injection, and transaction commit boundaries.
2. **Service Layer (`app/services/`)**: Framework-agnostic domain logic raising pure Python domain exceptions (`NotFoundError`, `ConflictError`, `CheckoutError`), mapped centrally in `app/main.py`.
3. **Persistence Layer (`app/models/`, `app/db/`)**: SQLAlchemy 2.0 declarative models (`Mapped[...]`), asynchronous session factory (`AsyncSession`), and Alembic migrations.
4. **Schema Layer (`app/schemas/`)**: Pydantic v2 input validation and response serialization (`from_attributes=True`).

### B. Concurrency & Inventory Protection (`POST /orders/checkout`)
- **Pessimistic Row-Level Locking**: Product inventory rows are locked via `select(Product).with_for_update().execution_options(populate_existing=True)`.
- **Deadlock Prevention**: Product IDs are sorted in ascending order (`Product.id.asc()`) prior to lock acquisition so concurrent transactions never form circular lock waits.
- **Lock Decoupling & Compensation**: Database locks are committed before initiating external Stripe network calls. If PaymentIntent creation fails, a compensating transaction cancels the order and restores inventory atomically.

### C. Caching & Background Workers
- **Cache-Aside Pattern**: `GET /products/{id}` (1h TTL) and `GET /products` (60s TTL) read through `redis.asyncio` and degrade gracefully to PostgreSQL if Redis is unreachable.
- **Active Invalidation**: Product creation and checkout stock updates evict affected `product:{id}` and `products:list:*` keys via `scan_iter`.
- **Asynchronous Task Queue**: Confirmed payment webhooks dispatch `send_order_confirmation_email.delay(order.id)` to Celery over Redis after the database transaction commits.

### D. Payment Processing (`app/services/payment.py`)
- **Stripe PaymentIntent**: Card details are handled client-side; the backend issues a `client_secret` calculated in integer cents (`int((order.total * 100).to_integral_value())`).
- **HMAC-SHA256 Webhook Verification**: `POST /payments/webhook` validates `Stripe-Signature` against raw request bytes (`await request.body()`) and processes `payment_intent.succeeded` events idempotently.

---

## 3. API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/signup` | Public | Register user with `bcrypt` password hashing (409 on duplicate email) |
| `POST` | `/auth/login` | Public | Authenticate user with constant-time dummy hash check, return JWT |
| `GET` | `/auth/me` | Bearer JWT | Retrieve authenticated user profile |
| `GET` | `/categories` | Public | List categories sorted by name |
| `POST` | `/categories` | Admin JWT | Create category (requires `role = 'admin'`) |
| `GET` | `/products` | Public | Paginated catalog with search (`q`), price bounds (`min_price`, `max_price`), `category_id`, and sort (`price_asc`, `price_desc`, `newest`) |
| `POST` | `/products` | Admin JWT | Create product and invalidate cached product listings (requires `role = 'admin'`) |
| `GET` | `/products/{id}` | Public | Retrieve single product details with eager-loaded category |
| `GET` | `/cart` | Bearer JWT | Retrieve or auto-create active user cart with computed totals |
| `POST` | `/cart/items` | Bearer JWT | Add product to cart or increment quantity with stock checks |
| `PATCH` | `/cart/items/{id}` | Bearer JWT | Update item quantity in active cart |
| `DELETE` | `/cart/items/{id}` | Bearer JWT | Remove item from active cart (`204 No Content`) |
| `POST` | `/orders/checkout` | Bearer JWT | Reserve stock under `FOR UPDATE` lock, snapshot items, create Stripe PaymentIntent |
| `POST` | `/payments/webhook` | Stripe Sig | Verify webhook signature, mark order confirmed, enqueue Celery confirmation task |
| `GET` | `/health` | Public | Application liveness check |
| `GET` | `/health/db` | Public | PostgreSQL connectivity check (`SELECT 1`) |

---

## 4. Database Schema

Managed via Alembic (`alembic/`):
- **`users`**: Credentials with functional unique index on `lower(email)`.
- **`categories`**: Product categories with unique non-empty name constraints.
- **`products`**: Catalog items with `Numeric(12, 2)` price and `stock >= 0` check constraints.
- **`carts`**: User cart sessions enforcing a partial unique index (`uq_carts_one_active_per_user WHERE status = 'active'`).
- **`cart_items`**: Line items tied to an active cart.
- **`orders`**: Order headers with monetary totals and `JSONB` shipping address.
- **`order_items`**: Immutable historical snapshots (`product_name`, `sku`, `unit_price`, `quantity`).
- **`payments`**: Payment state tracking (`provider`, `provider_payment_id`, `status`).

Schema references: [docs/architecture/schema.sql](docs/architecture/schema.sql) | [docs/architecture/Schema.jpg](docs/architecture/Schema.jpg)

---

## 5. Getting Started

### Environment Variables (`.env`)
```ini
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/commerce
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your_jwt_secret_key
STRIPE_SECRET_KEY=sk_test_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_secret
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Run with Docker Compose
```bash
docker compose up --build -d
```
Starts `postgres`, `redis`, runs `alembic upgrade head`, boots `api` on `http://localhost:8000` (Swagger UI at `/docs`), and starts `celery_worker`.

### Run Locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

alembic upgrade head
uvicorn app.main:app --reload
celery -A app.worker.celery_app worker --loglevel=info
```

### Run Tests
Requires a local PostgreSQL instance (uses isolated `commerce_test` database) and Redis:
```bash
pytest -v
```
