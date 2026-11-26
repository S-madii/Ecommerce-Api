---
tags:
  - hub
  - dashboard
  - commerce-api
---

# 🚀 Commerce API — Technical Knowledge Vault

Welcome to the internal engineering documentation and study vault for **commerce-api**. 
This vault serves as both the **system architecture specification** and your **personal technical revision hub**.

---

## 📌 Master Documents

- 🗺️ [[roadmap|Project Roadmap (A1 – A9)]] — The end-to-end technical specification across all 9 milestones.
- 📖 [[README|Architecture & API Reference]] — System architecture diagrams, 4-tier design patterns, and endpoint catalog.
- 📈 [[PROGRESS|Progress Tracker]] — Live sprint tracker and working agreements.

---

## 📚 Phase-by-Phase Revision Notes

Quick-reference study sheets covering decisions, code patterns, and traps from every completed milestone:

| Phase | Milestone | Key Concepts & Patterns | Note Link |
| :---: | :--- | :--- | :---: |
| **A1** | Project Foundations | Async engine, `pydantic-settings`, `SecretStr`, `get_db` generator | [[notes/A1_foundations\|A1: Foundations]] |
| **A2** | Schema Design | 9 tables, case-insensitive `lower(email)`, partial index on active carts | [[notes/A2_schema_design\|A2: Schema Design]] |
| **A3** | SQLAlchemy & Alembic | 2.0 `Mapped[...]`, rollback round-trip testing, migration chains | [[notes/A3_sqlalchemy_alembic\|A3: Migrations]] |
| **A4** | Stateless JWT Auth | Direct `bcrypt`, dummy hash timing attack guard, `PyJWT`, `IntegrityError` rollback | [[notes/A4_jwt_auth\|A4: JWT Auth]] |
| **A5** | Product Catalog | `selectinload` eager loading, multi-filters (`icontains`), safe sorting, envelopes | [[notes/A5_catalog_queries\|A5: Catalog & Filters]] |
| **A6** | Cart & Concurrency | `SELECT ... FOR UPDATE`, sorted deadlock prevention, price snapshots | [[notes/A6_concurrency_checkout\|A6: Concurrency & Checkout]] |
| **A7** | Stripe Payments | Zero-trust PaymentIntent, integer cents math, `db.flush()`, HMAC webhooks | [[notes/A7_stripe_payments\|A7: Stripe Payments]] |
| **A8** | Caching & Celery | Async Redis pool, cache-aside pattern, active invalidation, Celery IPC worker | [[notes/A8_redis_celery\|A8: Caching & Workers]] |
| **A9.1** | Architecture Hardening | Domain exceptions, global translation, transaction boundary, pagination defense | [[notes/A9_production_architecture_hardening\|A9.1: Architecture Hardening]] |
| **A9.2** | Docker & Compose | Layer caching, `0.0.0.0` binding, internal DNS networking, healthchecks, volumes | [[notes/A9_docker_containerization\|A9.2: Docker & Compose]] |
| **A9.3** | Async Testing (`pytest`) | `ASGITransport`, `dependency_overrides`, `commerce_test` isolation, `asyncio.gather` lock tests | [[notes/A9_pytest_asyncio_testing\|A9.3: Async Testing]] |

---

## 🧠 Comprehensive Deep Dives

- ⚡ [[learning/SKILL|The Master SKILL Reference]] — Full 9-part cheat sheet with diagrams and code recipes.
- 🔐 [[learning/LEARN_jwt_auth|Deep Dive: JWT & Cryptographic Hashing]]
- 📦 [[learning/LEARN_catalog|Deep Dive: Catalog Pagination & Safe Sorting]]
- 🗄️ [[learning/LEARN_sqlalchemy_alembic|Deep Dive: Asyncpg, SQLAlchemy 2.0 & Alembic]]
- ⚙️ [[learning/FastApi_Async_Foundation|Deep Dive: FastAPI & Async Event Loops]]

---

## 🏛️ Database Architecture
- 📜 [[architecture/schema.sql|Raw SQL Schema]]
- 🖼️ `docs/architecture/Schema.jpg` (Visual ERD)

---
*Tip in Obsidian: Press `Ctrl + G` to view the interactive Graph View of how all your notes, concepts, and phases interconnect!*
