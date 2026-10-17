# Learn: SQLAlchemy + Alembic (from zero)

Read this top to bottom. Each part has **Do** steps. Don't skip ahead — every step works and is tested before the next one.

---

## Part 0 — The big idea: what is an ORM?

In Notes you wrote SQL by hand:

```python
cursor.execute("INSERT INTO users (email, password_hash) VALUES (%s, %s)", (email, pw))
cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
row = cursor.fetchone()          # row is a tuple/dict
print(row["email"])
```

With an **ORM** (Object-Relational Mapper) you describe each table **once** as a Python class. Then you work with Python objects, and SQLAlchemy writes the SQL for you:

```python
user = User(email=email, password_hash=pw)   # a Python object = one future row
session.add(user)                            # "please save this"
await session.commit()                       # SQLAlchemy writes the INSERT

result = await session.execute(select(User).where(User.email == email))
user = result.scalar_one()                   # user is a User object, not a tuple
print(user.email)
```

Same database, same SQL underneath. You still need to understand SQL — the ORM just saves typing and catches mistakes (typos in column names become Python errors instead of runtime SQL errors).

**Four pieces you'll build, and what each one is:**

| Piece | File | Real-world analogy |
|---|---|---|
| **Base** | `db/base.py` | The registry book where every table gets written down |
| **Engine** | `db/session.py` | The phone line to Postgres (kept open, reused) |
| **Session** | `db/session.py` | One phone call: a conversation for one request |
| **Models** | `models/*.py` | The description of each table |

And **Alembic** = the tool that reads your models and creates/changes the real tables in Postgres.

---

## Part 1 — Base

**Do:** create `app/db/base.py`:

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

That's it. Every model will inherit from `Base`. When a class inherits from it, SQLAlchemy writes that table into `Base.metadata` — a list of every table your app has. Alembic reads `Base.metadata` later to know what tables should exist.

*Why its own file:* models need it and Alembic needs it, but neither should have to open a database connection just to get it.

---

## Part 2 — Engine, session, and get_db

This file is **boilerplate**: almost identical in every FastAPI project. You don't need to invent it — you need to understand it.

**Do:** create `app/db/session.py`:

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# 1. The engine: a pool of open connections to Postgres. Created ONCE.
engine = create_async_engine(settings.DATABASE_URL, echo=True)

# 2. A factory that produces sessions on demand.
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


# 3. FastAPI dependency: one session per request, always closed afterwards.
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
```

Line by line:

- `create_async_engine(url, echo=True)` — builds the connection pool from your `.env` URL. `echo=True` prints every SQL query in your terminal. Keep it on while learning: you'll *see* what SQLAlchemy does.
- `async_sessionmaker(engine, ...)` — not a session, a **factory**. Calling `SessionLocal()` gives you a fresh session.
- `expire_on_commit=False` — by default, after `commit()` SQLAlchemy "forgets" the values of your objects and reloads them on next access. In async code that surprise-reload crashes. This turns it off.
- `get_db()` — a **generator** (it uses `yield`). FastAPI runs it like this:
  1. request arrives → code runs up to `yield` → the session is handed to your endpoint
  2. endpoint finishes (or crashes) → code continues after `yield` → `async with` closes the session
  
  So the session is **always** closed, even on errors. That's why `yield`, not `return`.

**Do:** add a database health check in `app/main.py`:

```python
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

app = FastAPI(title="Commerce API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
async def health_db(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"database": "ok"}
```

- `Depends(get_db)` = "FastAPI, before calling this function, run `get_db()` and give me what it yields."
- `text("SELECT 1")` = run raw SQL. `SELECT 1` is the classic "are you alive?" query.
- `await` = this talks to the network (Postgres), so we wait for it without blocking other requests.

**Test:** `uvicorn app.main:app --reload` → open `http://127.0.0.1:8000/health/db` → `{"database":"ok"}`. Look at your terminal: you'll see `SELECT 1` printed by `echo=True`.

Then stop Postgres (`sudo systemctl stop postgresql`), refresh, look at the result, start it again (`sudo systemctl start postgresql`).

**Commit.**

---

## Part 3 — Your first model, line by line

We build **only `User`** first. One table, fully understood, migrated, and played with. Then the rest.

Here's the spec from `schema.sql`:

```sql
CREATE TABLE users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20),
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX uq_users_email_lower ON users (LOWER(email));
CREATE UNIQUE INDEX uq_users_phone ON users (phone_number) WHERE phone_number IS NOT NULL;
```

**Do:** create `app/models/user.py`:

```python
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(255))
    phone_number: Mapped[str | None] = mapped_column(String(20))
    password_hash: Mapped[str] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("uq_users_email_lower", func.lower(email), unique=True),
        Index(
            "uq_users_phone",
            "phone_number",
            unique=True,
            postgresql_where=text("phone_number IS NOT NULL"),
        ),
    )
```

Now the SQL ↔ Python translation, piece by piece:

| SQL | Python | Meaning |
|---|---|---|
| `CREATE TABLE users` | `class User(Base)` + `__tablename__ = "users"` | Class name = how you use it in Python. `__tablename__` = real table name |
| `id BIGINT ... IDENTITY PRIMARY KEY` | `mapped_column(BigInteger, Identity(always=True), primary_key=True)` | Big auto-numbered ID, Postgres generates it |
| `VARCHAR(255)` | `String(255)` | Text with max length |
| `NOT NULL` | `Mapped[str]` | **No `None` in the type = NOT NULL.** SQLAlchemy reads your type hint! |
| *(nullable)* | `Mapped[str \| None]` | `\| None` = column can be empty |
| `TIMESTAMPTZ` | `DateTime(timezone=True)` | Date+time with timezone. Always use timezone=True |
| `DEFAULT NOW()` | `server_default=func.now()` | Postgres fills it in. `func.now()` = the SQL function `NOW()` |
| *(no SQL equivalent)* | `onupdate=func.now()` | When SQLAlchemy UPDATEs this row, it also sets `updated_at = NOW()` |
| `CREATE UNIQUE INDEX ... (LOWER(email))` | `Index("...", func.lower(email), unique=True)` | `func.anything()` = call that SQL function |
| `... WHERE phone_number IS NOT NULL` | `postgresql_where=text("...")` | Partial index: only checks rows matching the condition |

Two things to understand about the syntax:

- **`Mapped[...]`** is the *Python* type (what you get when you read `user.email`). **`mapped_column(...)`** holds the *database* details (length, defaults, keys). Together they define one column.
- **`__table_args__`** is where table-level things go: indexes and constraints that involve more than "one column's type". It must be a **tuple** — note the trailing commas.

**Do:** make `app/models/__init__.py`:

```python
from app.models.user import User

__all__ = ["User"]
```

Why: Alembic only sees tables whose class has been *imported*. This file is the one place that imports every model. `__all__` just lists what this package exports.

---

## Part 4 — Alembic: turn the model into a real table

**What Alembic is:** git for your database structure. Each change = one migration file (a Python script with `upgrade()` and `downgrade()`). Postgres remembers which migration it's at, in a small table called `alembic_version`.

**Do (from the repo root, venv active):**

```fish
alembic init -t async alembic
```

This creates:
- `alembic.ini` — Alembic's settings
- `alembic/env.py` — the script Alembic runs to connect to your DB and compare it with your models
- `alembic/versions/` — where migration files will appear (empty for now)

`-t async` = use the template for async drivers like `asyncpg`. (So `psycopg2-binary` is **not** needed — remove it from `requirements.txt`.)

**Do: edit `alembic/env.py`** — two changes.

Change 1. Near the top, after `config = context.config`, add:

```python
from app.core.config import settings

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
```

Why: the URL contains your password. `alembic.ini` gets committed to git, so the URL must **not** live there. This reads it from `.env` through your settings instead.

Change 2. Find the line `target_metadata = None` and replace it with:

```python
from app.db.base import Base
import app.models  # noqa: F401  (imports all models so Base.metadata knows every table)

target_metadata = Base.metadata
```

Why: `target_metadata` is "what the database *should* look like". Alembic compares it with what Postgres *actually* has, and writes the difference as a migration. `# noqa` tells linters "yes, I import this without using it, on purpose".

**Do: generate the first migration:**

```fish
alembic revision --autogenerate -m "create users table"
```

A new file appears in `alembic/versions/`. **Open it and read it.** You'll see:
- `upgrade()` with `op.create_table("users", ...)` and `op.create_index(...)` ×2
- `downgrade()` with the reverse: drop indexes, drop table

Check both indexes are there, including the `lower(email)` one and the `WHERE phone_number IS NOT NULL`. Autogenerate is a **draft written by a robot** — you're the reviewer.

**Do: apply it:**

```fish
alembic upgrade head
```

`head` = "the latest migration". Watch the terminal — you'll see the actual `CREATE TABLE` SQL.

**Do: look inside Postgres:**

```fish
psql -h localhost -U commerce -d commerce
```

```
\dt                      -- should show: users, alembic_version
\d users                 -- columns + both indexes
SELECT * FROM alembic_version;   -- the ID of the migration you just ran
\q
```

**Do: practice undo/redo:**

```fish
alembic downgrade -1     # undo the last migration → users table gone
alembic upgrade head     # redo → back
```

**Commit** (the `alembic/` folder and `alembic.ini` are part of the project).

---

## Part 5 — Play with it (this is where it clicks)

Create `playground.py` at the repo root (add `playground.py` to `.gitignore` — it's your scratch file):

```python
import asyncio

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal
from app.models import User


async def main():
    async with SessionLocal() as session:
        # INSERT
        user = User(email="Ali@Example.com", password_hash="not-a-real-hash")
        session.add(user)
        await session.commit()
        await session.refresh(user)      # reload values Postgres generated (id, created_at)
        print("created:", user.id, user.email, user.created_at)

        # SELECT
        result = await session.execute(select(User).where(User.id == user.id))
        found = result.scalar_one()
        print("found:", found.email)

        # UPDATE
        found.phone_number = "0555123456"
        await session.commit()
        await session.refresh(found)
        print("updated_at changed:", found.updated_at)

        # Try to break the case-insensitive unique email
        session.add(User(email="ali@example.com", password_hash="x"))
        try:
            await session.commit()
        except IntegrityError as e:
            await session.rollback()
            print("Postgres refused duplicate email:", e.orig)


asyncio.run(main())
```

Run it: `python playground.py`. With `echo=True` you'll see **every SQL statement** SQLAlchemy generates — compare them with what you'd have written by hand in Notes.

Things to notice:
- `session.add()` doesn't send anything yet. `commit()` does.
- `select(User).where(User.id == ...)` — `User.id == 5` isn't a True/False here; SQLAlchemy turns it into SQL `WHERE users.id = 5`.
- `scalar_one()` = "give me exactly one object, error if 0 or 2+".
- The duplicate email (different capitals!) is refused **by Postgres**, thanks to your `LOWER(email)` index.

Run it twice. What happens the second time, and why? (Then clean up: `psql` → `DELETE FROM users;`)

---

## Part 6 — The other 7 models (your turn)

Now you know the pattern. New things you'll need:

**Foreign key** (a column pointing at another table):
```python
category_id: Mapped[int | None] = mapped_column(
    BigInteger, ForeignKey("categories.id", ondelete="SET NULL")
)
```
`"categories.id"` = table name + column (the SQL names, not the class name).

**Check constraint** (goes in `__table_args__`):
```python
CheckConstraint("stock >= 0", name="chk_products_stock"),
```
Always give constraints a `name` — error messages and future migrations refer to them by name.

**Unique pair:**
```python
UniqueConstraint("cart_id", "product_id", name="uq_cart_product"),
```

**Money:** `Mapped[Decimal]` + `Numeric(12, 2)` (`from decimal import Decimal`).

**Default value for a plain column:** `server_default=text("'active'")` (string — note the inner quotes) or `server_default=text("0")` (number).

**Relationship** (Python-side shortcut between linked objects — no column is created):
```python
# in Cart:
items: Mapped[list["CartItem"]] = relationship(back_populates="cart")
# in CartItem:
cart: Mapped["Cart"] = relationship(back_populates="items")
```
Now `cart.items` gives you a list of items and `item.cart` gives you the cart. Each side names the other in `back_populates`. Class names are in quotes because the other class might be in another file — SQLAlchemy looks them up once all models are imported (another job of `models/__init__.py`). Import with `from sqlalchemy.orm import relationship`.

**Do:**
1. Write `product.py` (Category, Product) **by yourself**, from `schema.sql`. Only after it works, compare with the ChatGPT version to see what you missed.
2. Add them to `models/__init__.py`.
3. `alembic revision --autogenerate -m "create categories and products"` → read → `alembic upgrade head` → `\dt` in psql.
4. Same for `cart.py` (Cart, CartItem) → migration.
5. Same for `order.py` (Order, OrderItem, Payment) → migration.

Notice: **one migration per step**, not one giant one. That's how real projects grow — and `alembic history` will show your schema's story.

---

## Cheat sheet

| I want to… | Command |
|---|---|
| Create a migration from model changes | `alembic revision --autogenerate -m "message"` |
| Apply all pending migrations | `alembic upgrade head` |
| Undo the last migration | `alembic downgrade -1` |
| See current DB version | `alembic current` |
| See all migrations | `alembic history` |

**Golden rule:** never edit a migration that has already been applied and shared. Need a change? Edit the model → create a **new** migration.
