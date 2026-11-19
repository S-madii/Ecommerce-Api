---
name: docs
description: 
---

# SKILL: Concepts Learned in `commerce-api`

A concise reference manual for all core patterns, architectures, and lessons learned through Phases A1 to A6.

---

## 1. FastAPI Architecture & Dependency Injection

### The 4-Layer Mental Model for Imports

Whenever creating a router, import across 4 separate layers:

1. **HTTP/Routing:** `APIRouter, Depends, HTTPException, status, Query` from `fastapi`
2. **Database Querying:** `select, func, AsyncSession` from `sqlalchemy` and `sqlalchemy.ext.asyncio`
3. **Data Contracts:** Schemas (e.g. `ProductCreate`, `CartRead`) and Models (e.g. `Product`, `Order`)
4. **App Services:** `get_db` from `app.db`, `get_current_user` from `app.core.security`

### Central Master Router Pattern (`app/routers/__init__.py`)

Individual routers define relative root paths (`@router.get("")`), then a central `api_router` mounts them with their
respective prefixes and tags:

```python
# app/routers/__init__.py
api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(cart_router, prefix="/cart", tags=["cart"])
api_router.include_router(order_router, prefix="/orders", tags=["orders"])

# app/main.py
app.include_router(api_router)
```

---

## 2. Pydantic v2 Contracts vs SQLAlchemy ORM

### Why Separate?

- **Models (`app/models/`)**: Represent PostgreSQL tables, constraints, foreign keys, and indexes.
- **Schemas (`app/schemas/`)**: Represent the API boundary contract (what clients can send and what is returned).

### `from_attributes=True`

Tells Pydantic to read object attributes (`user.id`) rather than dictionary keys (`user["id"]`):

```python
from pydantic import BaseModel, ConfigDict


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
```

### Response Envelopes

Do **not** need `from_attributes=True` if you instantiate them directly with plain Python arguments:

```python
class ProductList(BaseModel):
    items: list[ProductRead]
    total: int
    limit: int
    offset: int


# In router:
return ProductList(items=products, total=total, limit=limit, offset=offset)
```

---

## 3. Password Hashing & Direct `bcrypt`

Passlib is unmaintained. Use `bcrypt` directly:

- **Hashing on Signup:**
  ```python
  import bcrypt
  hashed_bytes = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
  password_hash = hashed_bytes.decode("utf-8") # store in DB
  ```
- **Verifying on Login:**
  ```python
  is_valid = bcrypt.checkpw(plain_password.encode("utf-8"), db_hash.encode("utf-8"))
  ```
- **Timing Attack Mitigation:**
  If a user is not found during login, run `bcrypt.checkpw(password.encode("utf-8"), DUMMY_HASH)` anyway so database
  search misses take the exact same time as incorrect password attempts.

---

## 4. Stateless JWT Authentication (`PyJWT`)

### JWT Structure

`header.payload.signature` signed with HMAC-SHA256 (`HS256`). A JWT is **signed**, not encrypted—never put secrets
inside the payload.

### Token Creation

```python
import jwt
from datetime import datetime, timezone, timedelta


def create_access_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {"sub": str(user_id), "exp": int(exp.timestamp())}
    return jwt.encode(payload, settings.SECRET_KEY.get_secret_value(), algorithm="HS256")
```

### Dependency Guard (`get_current_user`)

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer_scheme = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
                           db: AsyncSession = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY.get_secret_value(), algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    ...
```

---

## 5. PostgreSQL & Async SQLAlchemy 2.0

### Avoiding Race Conditions on Uniqueness

Don't check with `SELECT` before `INSERT`. Rely on PostgreSQL unique indexes and catch `IntegrityError` on `commit()`:

```python
from sqlalchemy.exc import IntegrityError

db.add(new_user)
try:
    await db.commit()
except IntegrityError:
    await db.rollback()  # Always rollback poisoned sessions!
    raise HTTPException(status_code=409, detail="Email already registered")
```

### The `MissingGreenlet` Async Trap & Eager Loading

In async SQLAlchemy, relationships default to lazy loading. When Pydantic serializes a relationship (`product.category`
or `cart.cart_items.product`), SQLAlchemy cannot fire synchronous background queries.

- **Fix:** Eager load upfront using `selectinload`:
  ```python
  from sqlalchemy.orm import selectinload

  stmt = (
      select(Cart)
      .options(selectinload(Cart.cart_items).selectinload(CartItem.product))
      .where(Cart.user_id == user_id, Cart.status == "active")
  )
  ```
- After creating a new record:
  ```python
  await db.refresh(new_product, attribute_names=["category"])
  ```

---

## 6. Dynamic Queries, Search, & Safe Sorting

### Shared `conditions` Pattern

Always apply the same filter list to both the `count` query and the `page` query:

```python
conditions = [Product.is_active == True]
if q:
    conditions.append(Product.name.icontains(q, autoescape=True))  # ILIKE + escapes % and _
if category_id is not None:
    conditions.append(Product.category_id == category_id)

# 1. Total count
total = await db.scalar(select(func.count()).select_from(Product).where(*conditions)) or 0

# 2. Page query
query = (
    select(Product)
    .options(selectinload(Product.category))
    .where(*conditions)
    .order_by(sort_criterion, Product.id.asc())  # id tiebreaker prevents paging jitter
    .limit(limit)
    .offset(offset)
)
```

### Safe Sorting Whitelist

Never use `getattr(Model, sort)` on user input:

```python
from typing import Literal

SORT_MAP = {
    "price_asc": Product.price.asc(),
    "price_desc": Product.price.desc(),
    "newest": Product.created_at.desc(),
}

# Parameter in router:
sort: Literal["price_asc", "price_desc", "newest"] = "newest"
sort_criterion = SORT_MAP[sort]
```

---

## 7. Shopping Cart Mechanics & Multi-Tenancy

### 1 Active Cart Constraint

Database partial index:

```python
Index("uq_carts_one_active_per_user", "user_id", unique=True, postgresql_where=text("status = 'active')"))
```

Guarantees a buyer has at most 1 active cart. Converted/abandoned carts do not block creating a new one.

### Dynamic Computations vs Stored Columns

`CartItem` in the database does not store subtotal or product name—those change over time! Compute them on the fly from
the eager-loaded product:

```python
subtotal = item.product.price * item.quantity
```

### Multi-Tenancy Scoping on Mutation & Deletion

Never query just by `CartItem.id == item_id`. A malicious user could modify someone else's cart by guessing IDs. Always
scope to the user's active cart:

```python
stmt = select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id)
```

---

## 8. Concurrency, Pessimistic Row Locking & Checkout (A6)

### The Overselling Problem

Without concurrency locks, two concurrent checkouts on the last remaining stock item (`stock = 1`) will both read `1`,
both deduct, and result in `stock = -1` (overselling).

### Pessimistic Locking with `SELECT ... FOR UPDATE`

Locks the selected rows in PostgreSQL memory until the current transaction commits or rolls back:

```python
stmt = (
    select(Product)
    .where(Product.id.in_(product_ids))
    .order_by(Product.id.asc())
    .with_for_update()
)
result = await db.execute(stmt)
locked_products = result.scalars().all()
```

### Deadlock Elimination

If Tx A locks Product 1 then waits for Product 2, while Tx B locks Product 2 and waits for Product 1, PostgreSQL crashes
with a deadlock.

- **Rule:** Always sort product IDs in numerical order (`Product.id.asc()`) before locking. Every transaction locks rows
  in the exact same sequence, making deadlocks mathematically impossible.

### Immutable Price Snapshots (`OrderItem`)

Store prices change over time, but legal receipts and order history must never mutate.

- **Pattern:** When checkout succeeds, copy the current price and product details into `OrderItem`:
  ```python
  OrderItem(
      product_id=product.id,
      product_name=product.name,  # frozen snapshot
      sku=product.sku,            # frozen snapshot
      unit_price=product.price,   # frozen snapshot
      quantity=cart_item.quantity
  )
  ```

### Atomic Cart Conversion

In the same transaction:

1. `product.stock -= item.quantity`
2. Create `Order` and `OrderItem` records
3. `cart.status = "converted"`
4. `await db.commit()` $\rightarrow$ all row locks are automatically released and changes persist atomically. If
   anything fails, `await db.rollback()` reverts stock and releases locks immediately.
