# LEARN: Product catalog, pagination, filtering (A5a)

Read this offline. Write the code yourself. Hints are at the end, only if you're stuck.

Scope of this doc: the **public, read-only** side of the catalog. Admin create and update (A5b) comes in a later doc, because it needs an admin flag on `users` first.

---

## Part 1: Output schemas for a resource with a relationship

### THEORY
A product belongs to a category. When a client asks for a product, it usually wants the category name too, not just `category_id: 7`. You can **nest** one schema inside another: the product schema has a `category` field whose type is the category schema.

### WHY
- The client gets everything it needs in one request.
- You still control exactly which category fields leak out (`id` and `name`, not `created_at`).

### HOW IT WORKS
- Both schemas need `from_attributes=True`, because Pydantic reads `product.category.name` from ORM objects.
- If the relationship can be empty (a product with no category), the field type must allow `None`.
- **Money:** your `price` column is `Numeric(12, 2)` and maps to Python `Decimal`, not `float`. Floats can't represent `0.10` exactly. Pydantic v2 turns `Decimal` into a **string** in JSON. Clients must be ready for `"19.99"`, not `19.99`. That's on purpose: it keeps the exact value.

### SMALL EXAMPLE (not your project)

```python
class AuthorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str

class BookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    price: Decimal
    author: AuthorRead | None
```

### YOUR PROJECT
Look at `app/models/product.py`. Which columns are useful to a shopper? Which are internal (think about `is_active`, timestamps)? Also check the type hint on `description` against its `nullable=` setting. Do they agree?

---

## Part 2: Relationships in async SQLAlchemy (the trap)

### THEORY
By default a relationship is **lazy**: `book.author` is not loaded until you touch it. With a sync session, touching it quietly runs a second query. With an **async** session that's not allowed, because a hidden query would need an `await` that isn't there. You get an error, usually `MissingGreenlet`.

The catch: *you* never write `book.author` in your route. **Pydantic** does, when it serializes the response. So the error shows up at response time, which is confusing the first time.

### WHY
You must tell SQLAlchemy up front which relationships to load. That's called **eager loading**.

### HOW IT WORKS
- `selectinload(Model.relationship)` runs one extra query: `SELECT ... FROM authors WHERE id IN (...)` for all the books at once.
- You attach it to the statement with `.options(...)`.
- One extra query for the whole page, not one per row. The "one per row" version is called the **N+1 problem**, and you're avoiding it here.

### SMALL EXAMPLE (not your project)

```python
from sqlalchemy.orm import selectinload

stmt = select(Book).options(selectinload(Book.author)).where(Book.id == book_id)
```

### YOUR PROJECT
Write the detail route *without* `selectinload` first, call it, and read the error. Then add it. You'll recognize this error forever after.

---

## Part 3: Pagination with limit and offset

### THEORY
Never return a whole table. The client asks for a **page**: `limit` (how many) and `offset` (how many to skip).

- Page 1: `limit=20&offset=0`
- Page 2: `limit=20&offset=20`

### WHY
- A table with 50,000 products would kill the response time and the client's memory.
- **Response metadata** (`total`, `limit`, `offset`) lets a frontend draw "page 3 of 12" without guessing.

### HOW IT WORKS
- Validate the query parameters so a client can't ask for `limit=1000000` or a negative offset. FastAPI's `Query(ge=..., le=...)` rejects bad values with 422 before your code runs.
- **Always `ORDER BY`.** SQL gives no row order guarantee without it. Without ordering, the same product can appear on page 1 *and* page 2, or on neither.
- The `total` needs a **second query**: `SELECT count(*)` with the **same filters** as the page query, but without limit and offset.
- Wrap the result in an envelope schema: `items` plus the metadata.

### SMALL EXAMPLE (not your project)

```python
from typing import Annotated
from fastapi import Query
from sqlalchemy import func, select

@router.get("/books", response_model=BookPage)
async def list_books(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(get_db),
):
    total = await db.scalar(select(func.count()).select_from(Book))
    stmt = select(Book).order_by(Book.id).limit(limit).offset(offset)
    books = (await db.execute(stmt)).scalars().all()
    return BookPage(items=books, total=total, limit=limit, offset=offset)
```

### Limitation to know (not to fix now)
Offset gets slow on deep pages (`offset=100000` still scans 100,000 rows), and rows shift if something is inserted between page loads. The fix is **keyset (cursor) pagination**: "give me 20 after id 4521". You don't need it for a shop MVP, but you should be able to name it.

### YOUR PROJECT
Your `products` table already has an index on `is_active` and one on `category_id`. Think about which `ORDER BY` column is cheap and gives every row a unique position.

---

## Part 4: Filtering and search

### THEORY
Filters are optional query parameters. If the client sends one, add a `WHERE` condition. If not, skip it. You build the statement **step by step**.

### WHY
One endpoint (`GET /products?q=shirt&category_id=3&max_price=50`) covers all the shop's browsing needs. You don't need a separate route per filter.

### HOW IT WORKS
- Collect conditions in a list, then apply them with `.where(*conditions)`.
- Use the **same** list for the count query and the page query. That's what keeps `total` honest.
- **Search:** `ILIKE` is case-insensitive pattern matching. SQLAlchemy 2.0 has `.icontains(text, autoescape=True)`. Why `autoescape`: in `LIKE`, `%` and `_` are wildcards. A user typing `100%` would match more than they meant. `autoescape=True` treats their input as plain text.
- **Public endpoints show only active products.** That condition is always applied, not optional.

### SMALL EXAMPLE (not your project)

```python
conditions = [Book.is_published.is_(True)]
if q:
    conditions.append(Book.title.icontains(q, autoescape=True))
if max_price is not None:
    conditions.append(Book.price <= max_price)

stmt = select(Book).where(*conditions).order_by(Book.id)
```

Note `is not None` for numbers: `if max_price:` would skip a filter of `0`.

### Performance note (not to fix now)
`ILIKE '%shirt%'` can't use a normal index, so Postgres scans every row. That's fine for a few thousand products. At larger sizes, the fix is the `pg_trgm` extension with a trigram index. Just know the name.

### YOUR PROJECT
Decide which filters a shopper at a small shop actually uses. Name search, category, and a price range cover most of it.

---

## Part 5: Sorting safely

### THEORY
Clients want `sort=price` or `sort=-price` (descending). The dangerous shortcut is turning the client's string straight into a column, like `getattr(Product, sort)`.

### WHY
With `getattr`, a client can sort by **any** attribute, including ones you never meant to expose, and you get 500 errors on typos. The safe pattern is a **whitelist**: a dict that maps allowed sort names to columns. Anything else gets a 422 or falls back to the default.

### HOW IT WORKS
- Map names to columns: `{"price": Book.price, "newest": Book.created_at}`.
- Always add a unique **tiebreaker** (`id`) after the sort column. Two books with the same price need a fixed order, or pagination breaks again (same problem as Part 3).
- FastAPI can validate the value for you if the parameter type is a `Literal[...]` or an `Enum`.

### YOUR PROJECT
Pick two or three sort options a shopper would use. Not every column deserves one.

---

## Part 6: The detail route and 404

### THEORY
`GET /products/{id}` returns one product, or 404.

### WHY
Inactive products should look like they **don't exist** to the public. Same idea as your login 401: don't reveal internal state. A deactivated product returns 404, not 403 or "this product is inactive".

### YOUR PROJECT
You already have `NotFoundError` in `app/core/exceptions.py`. This is its first real use.

---

## New files in this phase

| File | Purpose | Why separate | Who imports it |
|------|---------|--------------|----------------|
| `app/schemas/product.py` | Product and category output schemas, page envelope | Same reason as `schemas/user.py`: the API contract is not the table | `routers/products.py` |
| `app/routers/products.py` | Catalog routes | One router per resource keeps `main.py` small and lets each resource have its own prefix and tag | `main.py` (via `include_router`) |

Creation order: schemas first (the router imports them), then the router, then register it in `main.py`.

---

## Hints (only if stuck)

- **Hint 1:** `CategoryRead` only needs two fields. The product schema's `category` field type is `CategoryRead | None`.
- **Hint 2:** If the detail route throws an error about greenlets, you forgot `.options(selectinload(Product.category))`.
- **Hint 3:** `await db.scalar(stmt)` returns a single value, which is perfect for `count(*)`.
- **Hint 4:** For the count, `select(func.count()).select_from(Product).where(*conditions)`.
- **Hint 5:** For sorting, a `Literal["price", "-price", "newest"]` parameter type makes FastAPI reject anything else with 422 automatically.
