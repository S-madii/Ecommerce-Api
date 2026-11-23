# Notes: Phase A5 — Product Catalog, Dynamic Filtering & Eager Loading

## Key Decisions
- **Eager Loading with `selectinload`**: Solved the async `MissingGreenlet` error. Async sessions cannot execute implicit background queries when Pydantic touches a relationship (`product.category`).
- **Response Envelope**: Used `ProductList` with `items`, `total`, `limit`, and `offset` so the frontend knows total page count.
- **Shared Query Conditions**: Maintained a single `conditions = [Product.is_active == True]` list used by **both** the count query and the data query.

## Common Traps & Lessons
- **Wildcard Injection in Search (`ILIKE`)**:
  Using `Product.name.contains(q)` is case-sensitive and vulnerable to wildcard characters (`%`, `_`).
  - **Fix**: Use `Product.name.icontains(q, autoescape=True)`.
- **Safe Sorting Whitelist**:
  Never do `getattr(Product, sort)` on raw client input (security hazard & 500 error risk).
  - **Fix**: Validate via `Literal["price_asc", "price_desc", "newest"]` and map via a whitelist dictionary:
    ```python
    SORT_MAP = {
        "price_asc": Product.price.asc(),
        "price_desc": Product.price.desc(),
        "newest": Product.created_at.desc(),
    }
    ```
- **Deterministic Pagination Tiebreakers**:
  If two products have the exact same price (`$19.99`), Postgres does not guarantee their order across pages. Always append a unique secondary tiebreaker: `.order_by(sort_criterion, Product.id.asc())`.
- **`from_attributes=True` vs Plain Models**:
  ORM models need `ConfigDict(from_attributes=True)` so Pydantic can read object attributes (`product.name`). Envelopes built with plain Python arguments (like `ProductList`) do not need it.
