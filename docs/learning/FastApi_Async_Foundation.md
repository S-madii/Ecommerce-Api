# FastAPI & Async Foundations
### Advanced Architectural Guide for E-Commerce Backend Systems

---

## Part 1: The Engine of Concurrency

In traditional, synchronous Python architectures (like older Django or Flask apps), a function runs from top to bottom, completely monopolizing the thread. If that function asks the database for a user record, the entire thread stops and waits. If a database query takes 100 milliseconds, that thread does nothing for 100 milliseconds. Under heavy load, this requires spinning up hundreds of threads, which consumes massive amounts of RAM and CPU overhead.

### The Restaurant Analogy

Imagine a restaurant where a waiter takes your order, walks to the kitchen, gives it to the chef, and then stands completely still in the kitchen waiting for your food to cook before serving you and moving to the next table. That is **synchronous programming**. **Asynchronous programming** is a waiter who drops the ticket in the kitchen and immediately goes to take orders from three other tables while the food cooks.

In Python, the "kitchen" is the database or an external API (I/O bounds). The "waiter" is the **Event Loop**. We use specific keywords to manage this flow:

- `async def`: This tells Python, "This function is a coroutine. It has the ability to pause its own execution and resume later."
- `await`: This is the pause button. It tells the Event Loop, "I am waiting on network traffic here. Take control and go run other code until my data arrives."

```python
async def health_db(db: AsyncSession = Depends(get_db)):
    # The thread pauses here, allowing FastAPI to
    # serve other users while Postgres processes SELECT 1
    await db.execute(text("SELECT 1"))
    return {"database": "ok"}
```

> **Answering the Guide Question: Why does `/health/db` need `async def` while `/health` does not?**
> Because `/health` just returns a static dictionary (CPU-bound, instantaneous). `/health/db` makes a network call to PostgreSQL. Without `async` and `await`, a slow database would freeze the entire API.

---

## Part 2: FastAPI Routing and Pydantic

FastAPI acts as the bridge between HTTP requests and your Python logic. It uses decorators to bind URLs to specific functions. But its true power lies in how it leverages standard Python type hints to perform automatic data validation, serialization, and documentation generation.

### Path vs. Query Parameters

When designing endpoints, data usually arrives in one of two ways within the URL. FastAPI distinguishes between them automatically based on your path decorator string:

- **Path Parameters**: Used to identify a specific resource. If you define `@app.get("/users/{user_id}")`, FastAPI knows `user_id` is part of the URL path itself.
- **Query Parameters**: Used to filter or modify a request. If you define a parameter in your function that is *not* in the path string (e.g., `limit: int = 10`), FastAPI expects it after a question mark: `/users?limit=10`.

```python
@app.get("/users/{user_id}")
async def get_user(user_id: int, include_history: bool = False):
    # user_id is a path parameter.
    # include_history is a query parameter.
    pass
```

### Automatic Validation (Pydantic)

Because you annotated `user_id: int`, FastAPI relies on a library called **Pydantic** to strictly enforce that rule. If a client requests `GET /users/abc`, your Python function never even executes. FastAPI automatically intercepts the request and returns a structured `422 Unprocessable Entity` JSON error explaining that `"abc"` is not a valid integer. This eliminates the need to write manual `if type(user_id) != int:` boilerplate in your routes.

> **Security Note:** FastAPI automatically converts Python dictionaries into JSON responses. If you return an entire SQLAlchemy `User` object from a route, FastAPI will serialize every column it finds — including the `password_hash`. You must explicitly construct the dictionary you want to expose.

---

## Part 3: Dependency Injection & Sessions

Dependency Injection (DI) sounds complex, but it is simply a pattern where a function receives the tools it needs from the outside, rather than creating them itself. In FastAPI, the `Depends()` function is the engine for this. It tells the framework to execute a dependency function before running your route, and pass the result directly into your route's parameters.

### The Database Session Generator

In web applications, database sessions must be strictly scoped to the HTTP request lifecycle. A session must be opened when the request arrives, and it must be closed when the request finishes, even if an error occurs. We achieve this using a **Python Generator** (a function with a `yield` statement).

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        # Phase 1: Setup. Connects to Postgres.
        # Yield hands the session to the route.
        yield session
        # Phase 2: Teardown. The route is done.
        # The 'async with' block guarantees closure.
```

When a route uses `db: AsyncSession = Depends(get_db)`, FastAPI halts right at the `yield`. Your route executes using that active session. Once your route returns its response, FastAPI resumes the `get_db` function, executing the teardown code to safely release the connection back to the database pool.

> **Answering the Guide Question: Why do we set `expire_on_commit=False`?**
> By default, when you commit a transaction, SQLAlchemy "expires" the Python object, meaning it deletes the data from memory. If you try to return that object as JSON after committing, SQLAlchemy will try to lazily fetch it again from the database, crashing your async application. Disabling this keeps the data in memory.

---

## Part 4: Exercise Implementation Guide

To synthesize these concepts, you must implement the `GET /users/{user_id}` route. This endpoint must securely fetch a user by their database ID, handle cases where the user does not exist, and safely return only non-sensitive data.

### Architectural Checklist

- **The Route**: Use `@app.get` and declare the path parameter exactly as `{user_id}`.
- **The Signature**: Ensure the function is `async def`, strongly type `user_id: int`, and inject the session using `db: AsyncSession = Depends(get_db)`.
- **The Query**: Construct an SQLAlchemy `select(User).where(User.id == user_id)` statement and `await db.execute(...)`.
- **Execution**: Use `.scalar_one_or_none()`. Unlike `.scalar_one()` (which throws a hard Python exception if no row is found), this method safely returns `None`, allowing you to manually trigger a clean `404` response.

### Scaffold Structure

Use this structural skeleton to guide your logic in `app/main.py`:

```python
from fastapi import HTTPException
from sqlalchemy import select
from app.models import User

@app.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    # 1. Build the select query targeting User.id
    # 2. Await the execution of the query
    # 3. Extract the result using scalar_one_or_none()
    # 4. If the result is None, raise HTTPException(404)
    # 5. Return a safe dictionary (id, email, created_at)
    pass
```