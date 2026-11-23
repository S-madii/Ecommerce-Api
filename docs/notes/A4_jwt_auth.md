---
tags:
  - notes
  - security
  - auth
  - jwt
---

# 🔐 Notes: Phase A4 — Stateless JWT Authentication & Security

> [!abstract] Overview
> Implementing stateless authentication with `PyJWT`, direct `bcrypt` password hashing, timing-attack countermeasures, and race-condition-free signup.

---

## 🛡️ Key Security Patterns

### 1. Direct `bcrypt` (No Passlib)
`passlib` is unmaintained and breaks on modern Python/bcrypt releases. We interface directly with `bcrypt`:
```python
# Hash on signup:
hashed_bytes = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
db_hash = hashed_bytes.decode("utf-8")

# Verify on login:
is_valid = bcrypt.checkpw(plain.encode("utf-8"), db_hash.encode("utf-8"))
```

### 2. Timing Attack Mitigation
> [!important] The Vulnerability
> When a user enters a nonexistent email, database lookups return `None` in <1ms. When an email exists, bcrypt takes ~150ms. Attackers measure latency to harvest valid customer emails.

**Countermeasure**: Run a dummy comparison against a precomputed static hash on lookup misses:
```python
DUMMY_HASH = hashpw(b"dummy_password", gensalt())

if user_db is None:
    checkpw(user.password.encode("utf-8"), DUMMY_HASH)
    raise HTTPException(status_code=401, detail="Invalid credentials")
```

### 3. Avoiding Race Conditions on Signup
Never execute `select(User).where(...)` before `INSERT`. Two concurrent requests will both pass the check.
- **Pattern**: Directly execute `INSERT`, let PostgreSQL enforce the unique index, catch `sqlalchemy.exc.IntegrityError`, call `await db.rollback()`, and return `409 Conflict`.

---

## 🔗 Related Notes & Deep Dives
- ⬅️ Previous: [[notes/A3_sqlalchemy_alembic|A3: SQLAlchemy & Alembic]]
- ➡️ Next Milestone: [[notes/A5_catalog_queries|A5: Catalog & Filters]]
- ⚡ [[learning/LEARN_jwt_auth|Deep Dive: JWT & Auth Guide]]
