# SKILL: Concepts Learned in `commerce-api`

A concise reference manual for all core patterns, architectures, and lessons learned through Phases A1 to A5.

---

## 1. FastAPI Architecture & Dependency Injection

### The 4-Layer Mental Model for Imports
Whenever creating a router, import across 4 separate layers:
1. **HTTP/Routing:** `APIRouter, Depends, HTTPException, status, Query` from `fastapi`
2. **Database Querying:** `select, func, AsyncSession` from `sqlalchemy` and `sqlalchemy.ext.asyncio`
3. **Data Contracts:** Schemas (e.g. `ProductCreate`, `ProductRead`) and Models (e.g. `Product`, `Category`)
4. **App Services:** `get_db` from `app.db.session`, `get_current_user` from `app.core.security`

### Sub-app Router Mounting
Define routes with relative root paths inside routers (`@router.get("")`), then mount them with a prefix in `app/main.py`:
```python
# app/routers/products.py
router = APIRouter()
@router.get("")
async def read_products(...): ...

# app/main.py
app.include_router(product_router, prefix="/products", tags=["products"])
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
  If a user is not found during login, run `bcrypt.checkpw(password.encode("utf-8"), DUMMY_HASH)` anyway so database search misses take the exact same time as incorrect password attempts.

---

## 4. Stateless JWT Authentication (`PyJWT`)

### JWT Structure
`header.payload.signature` signed with HMAC-SHA256 (`HS256`). A JWT is **signed**, not encrypted—never put secrets inside the payload.

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

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: AsyncSession = Depends(get_db)) -> User:
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
    await db.rollback() # Always rollback poisoned sessions!
    raise HTTPException(status_code=409, detail="Email already registered")
```

### The `MissingGreenlet` Async Trap & Eager Loading
In async SQLAlchemy, relationships default to lazy loading. When Pydantic serializes a relationship (`product.category`), SQLAlchemy cannot fire synchronous background queries.
- **Fix:** Eager load upfront using `selectinload`:
  ```python
  from sqlalchemy.orm import selectinload

  stmt = select(Product).options(selectinload(Product.category)).where(...)
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
    conditions.append(Product.name.icontains(q, autoescape=True)) # ILIKE + escapes % and _
if category_id is not None:
    conditions.append(Product.category_id == category_id)

# 1. Total count
total = await db.scalar(select(func.count()).select_from(Product).where(*conditions)) or 0

# 2. Page query
query = (
    select(Product)
    .options(selectinload(Product.category))
    .where(*conditions)
    .order_by(sort_criterion, Product.id.asc()) # id tiebreaker prevents paging jitter
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
