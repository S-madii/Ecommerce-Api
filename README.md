# Commerce API

![CI](https://github.com/S-madii/Ecommerce-Api/actions/workflows/ci.yml/badge.svg)

REST API for an e-commerce store built with FastAPI, PostgreSQL, Redis, Celery, and Stripe. It provides the backend needed to run a storefront: user authentication with customer/admin roles, a searchable product catalog, persistent shopping carts, concurrent checkout with inventory locking, payment webhooks, and background email tasks.

## Features

- **Authentication & Roles**: JWT login/signup with `bcrypt` password hashing, Redis-backed IP rate limiting (`429 Too Many Requests`), refresh token rotation (`/auth/refresh`), immediate Redis `jti` token revocation on logout (`/auth/logout`), and role-based access (`customer` and `admin`). The first admin can be bootstrapped via `ADMIN_EMAIL` in `.env`, and admins can promote or delete user accounts.
- **Product Catalog**: Paginated product listing with keyword search (`q`), category filtering, min/max price filters, and sorting (`newest`, `price_asc`, `price_desc`).
- **Redis Caching**: Product details and catalog queries use a cache-aside pattern via `redis.asyncio`. Cache keys are invalidated when products are created or stock changes at checkout. If Redis is unavailable, requests fall back to PostgreSQL.
- **Shopping Cart**: Persistent active cart per user with stock validation and automatic line-item and cart total calculation.
- **Concurrency-Safe Checkout**: Locks product rows during checkout using `SELECT ... FOR UPDATE` ordered by product ID to prevent race conditions (overselling the last item) and deadlocks. Order items store a snapshot of the product name, SKU, and price at purchase time.
- **Stripe Payments & Webhooks**: Creates a Stripe `PaymentIntent` on checkout (releasing DB locks before the network call and rolling back stock if Stripe fails). A `/payments/webhook` endpoint verifies the `Stripe-Signature` HMAC header on the raw payload and marks the order as confirmed.
- **Background Tasks**: After payment confirmation commits to the database, a Celery worker processes the order confirmation email task asynchronously via Redis.

## Tech Stack

- **API**: Python 3.12+, FastAPI, Pydantic v2
- **Database**: PostgreSQL 16, SQLAlchemy 2.0 (asyncpg), Alembic
- **Cache & Queue**: Redis 7, Celery
- **Payments**: Stripe API
- **Testing & DevOps**: pytest, pytest-asyncio, httpx, Docker Compose, GitHub Actions

## Project Structure

```text
├── alembic/               # Database migration scripts
├── app/
│   ├── core/              # Settings, JWT security, Redis client, domain exceptions
│   ├── db/                # Async SQLAlchemy engine and session dependency
│   ├── models/            # SQLAlchemy ORM models (User, Product, Category, Cart, Order, Payment)
│   ├── routers/           # FastAPI route handlers
│   ├── schemas/           # Pydantic request/response models
│   ├── services/          # Business logic (CartService, ProductService, OrderService, PaymentService)
│   ├── main.py            # FastAPI app entrypoint and exception handlers
│   └── worker.py          # Celery worker configuration and tasks
├── docs/architecture/     # PostgreSQL DDL schema reference (schema.sql) and ERD (schema.jpg)
├── tests/                 # Async integration and concurrency tests
├── Dockerfile
└── docker-compose.yml
```

## API Endpoints

| Method | Path | Access | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/signup` | Public | Register a new user account (rate-limited; auto-assigns `admin` if email matches `ADMIN_EMAIL`) |
| `POST` | `/auth/login` | Public | Log in and receive `access_token` and `refresh_token` (rate-limited) |
| `POST` | `/auth/refresh` | Public | Exchange a valid `refresh_token` for a new token pair (rotates & revokes old refresh token) |
| `POST` | `/auth/logout` | Authenticated | Revoke current access token `jti` in Redis for immediate invalidation |
| `GET` | `/auth/me` | Authenticated | Get current user profile and role |
| `PATCH` | `/auth/users/{id}/role` | Admin | Promote or demote a user's role (`customer` / `admin`) |
| `DELETE` | `/auth/users/{id}` | Admin | Delete a user account (`204 No Content`) |
| `GET` | `/categories` | Public | List all categories |
| `POST` | `/categories` | Admin | Create a category |
| `GET` | `/products` | Public | List products (`q`, `category_id`, `min_price`, `max_price`, `sort`, `limit`, `offset`) |
| `GET` | `/products/{id}` | Public | Get a single product by ID |
| `POST` | `/products` | Admin | Create a product and invalidate list cache |
| `GET` | `/cart` | Authenticated | View active cart and totals |
| `POST` | `/cart/items` | Authenticated | Add an item to the cart |
| `PATCH` | `/cart/items/{id}` | Authenticated | Update item quantity in the cart |
| `DELETE` | `/cart/items/{id}` | Authenticated | Remove an item from the cart |
| `POST` | `/orders/checkout` | Authenticated | Lock stock, create order, and return Stripe `client_secret` |
| `POST` | `/payments/webhook` | Stripe | Verify webhook signature, confirm order, trigger Celery task |
| `GET` | `/health` | Public | App health check |
| `GET` | `/health/db` | Public | Database connectivity check |

Database schema details can be found in [docs/architecture/schema.sql](docs/architecture/schema.sql) and [docs/architecture/schema.jpg](docs/architecture/Schema.jpg).

## Getting Started

### 1. Environment Variables

Copy the example environment file and fill in your keys:

```bash
cp .env.example .env
```

```ini
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/commerce
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your_jwt_secret_key
STRIPE_SECRET_KEY=sk_test_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_secret
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
AUTH_RATE_LIMIT_PER_MINUTE=10
ADMIN_EMAIL=admin@example.com
```

### 2. Run with Docker Compose

Starts PostgreSQL, Redis, runs Alembic migrations, and launches the FastAPI server and Celery worker:

```bash
docker compose up --build -d
```

The API will be available at `http://localhost:8000` (Swagger docs at `http://localhost:8000/docs`).

### 3. Run Locally (Without Docker)

Requires PostgreSQL and Redis running locally:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

alembic upgrade head
uvicorn app.main:app --reload
```

In a second terminal, start the Celery worker:

```bash
source .venv/bin/activate
celery -A app.worker.celery_app worker --loglevel=info
```

## Running Tests

Tests use an isolated `commerce_test` PostgreSQL database and test auth, RBAC, catalog filtering, Redis cache invalidation, concurrent checkouts (`asyncio.gather` on `stock=1`), and Stripe webhooks:

```bash
pytest -v
```
