# Notes: Phase A3 — SQLAlchemy 2.0 & Alembic Migrations

## Key Decisions
- **SQLAlchemy 2.0 Declarative Style**: Used modern `Mapped[type]` and `mapped_column()` syntax rather than legacy 1.x `Column(Type)`.
- **Relationship Back-populates**: Always specify `back_populates` on both sides of a relationship for clean bi-directional ORM navigation.
- **Alembic Revisions**: Revisions created sequentially:
  - Users
  - Categories & Products
  - Carts & Cart Items
  - Orders, Order Items, Payments

## Common Traps & Lessons
- **Rollback Testing**: Never assume a migration works just because `alembic upgrade head` succeeds. Always test `alembic downgrade -1` and upgrade again to ensure `downgrade()` drop scripts are clean.
- **Async Database Driver in Alembic**: `env.py` must use `async_engine_from_config` and `run_sync` to execute migrations over an asynchronous connection.
- **Base Metadata**: Alembic only detects tables that inherit from the exact `Base` imported into `env.py`.
