-- =========================================================
-- E-COMMERCE DATABASE SCHEMA
-- PostgreSQL
--
-- Reference specification only.
-- SQLAlchemy models + Alembic migrations are authoritative.
-- Do NOT run this file directly against the database.
--
-- updated_at columns are NOT maintained by triggers.
-- In SQLAlchemy they use:
--     server_default=func.now(), onupdate=func.now()
-- =========================================================


-- =========================================================
-- 1. USERS
-- =========================================================

CREATE TABLE users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    email VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20),
    password_hash VARCHAR(255) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Email uniqueness is case-insensitive.
CREATE UNIQUE INDEX uq_users_email_lower
    ON users (LOWER(email));

-- A phone number is unique when provided.
CREATE UNIQUE INDEX uq_users_phone
    ON users (phone_number)
    WHERE phone_number IS NOT NULL;


-- =========================================================
-- 2. CATEGORIES
-- =========================================================

CREATE TABLE categories (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    name VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_categories_name
        CHECK (LENGTH(TRIM(name)) > 0)
);


-- =========================================================
-- 3. PRODUCTS
-- =========================================================

CREATE TABLE products (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    sku VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,

    category_id BIGINT
        REFERENCES categories(id)
        ON DELETE SET NULL,

    price NUMERIC(12, 2) NOT NULL
        CHECK (price >= 0),

    stock INTEGER NOT NULL DEFAULT 0
        CHECK (stock >= 0),

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_products_name
        CHECK (LENGTH(TRIM(name)) > 0)
);

CREATE INDEX idx_products_category
    ON products(category_id);

CREATE INDEX idx_products_active
    ON products(is_active);


-- =========================================================
-- 4. CARTS
-- =========================================================

CREATE TABLE carts (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    user_id BIGINT NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,

    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN (
            'active',
            'converted',
            'abandoned'
        )),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- A user can have multiple historical carts,
-- but only one active cart at a time.
CREATE UNIQUE INDEX uq_carts_one_active_per_user
    ON carts(user_id)
    WHERE status = 'active';


-- =========================================================
-- 5. CART ITEMS
-- =========================================================

CREATE TABLE cart_items (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    cart_id BIGINT NOT NULL
        REFERENCES carts(id)
        ON DELETE CASCADE,

    product_id BIGINT NOT NULL
        REFERENCES products(id)
        ON DELETE RESTRICT,

    quantity INTEGER NOT NULL
        CHECK (quantity > 0),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_cart_product
        UNIQUE (cart_id, product_id)
);

CREATE INDEX idx_cart_items_product
    ON cart_items(product_id);


-- =========================================================
-- 6. ORDERS
-- =========================================================

CREATE TABLE orders (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Public identifier for URLs and external references.
    public_id UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,

    user_id BIGINT NOT NULL
        REFERENCES users(id)
        ON DELETE RESTRICT,

    status VARCHAR(30) NOT NULL DEFAULT 'pending'
        CHECK (status IN (
            'pending',
            'confirmed',
            'processing',
            'shipped',
            'delivered',
            'cancelled',
            'refunded'
        )),

    currency CHAR(3) NOT NULL DEFAULT 'DZD',

    subtotal NUMERIC(12, 2) NOT NULL
        CHECK (subtotal >= 0),

    shipping_amount NUMERIC(12, 2) NOT NULL DEFAULT 0
        CHECK (shipping_amount >= 0),

    total NUMERIC(12, 2) NOT NULL
        CHECK (total >= 0),

    -- Snapshot of the shipping address at checkout.
    shipping_address JSONB NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_orders_user_created
    ON orders(user_id, created_at DESC);

CREATE INDEX idx_orders_status_created
    ON orders(status, created_at DESC);


-- =========================================================
-- 7. ORDER ITEMS
-- =========================================================

CREATE TABLE order_items (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    order_id BIGINT NOT NULL
        REFERENCES orders(id)
        ON DELETE RESTRICT,

    -- Keep the order item if its product is deleted.
    product_id BIGINT
        REFERENCES products(id)
        ON DELETE SET NULL,

    -- Historical snapshots.
    product_name VARCHAR(255) NOT NULL,
    sku VARCHAR(100) NOT NULL,

    quantity INTEGER NOT NULL
        CHECK (quantity > 0),

    unit_price NUMERIC(12, 2) NOT NULL
        CHECK (unit_price >= 0),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_order_items_order
    ON order_items(order_id);

CREATE INDEX idx_order_items_product
    ON order_items(product_id);


-- =========================================================
-- 8. PAYMENTS
-- =========================================================

CREATE TABLE payments (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    order_id BIGINT NOT NULL
        REFERENCES orders(id)
        ON DELETE RESTRICT,

    provider VARCHAR(50) NOT NULL,
    provider_payment_id VARCHAR(255),

    amount NUMERIC(12, 2) NOT NULL
        CHECK (amount > 0),

    currency CHAR(3) NOT NULL DEFAULT 'DZD',

    status VARCHAR(30) NOT NULL DEFAULT 'pending'
        CHECK (status IN (
            'pending',
            'requires_action',
            'succeeded',
            'failed',
            'cancelled',
            'partially_refunded',
            'refunded'
        )),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_payment_provider
        CHECK (LENGTH(TRIM(provider)) > 0)
);

-- Prevent duplicate provider payment references.
CREATE UNIQUE INDEX uq_payment_provider_reference
    ON payments(provider, provider_payment_id)
    WHERE provider_payment_id IS NOT NULL;

CREATE INDEX idx_payments_order
    ON payments(order_id);

CREATE INDEX idx_payments_status
    ON payments(status);


-- =========================================================
-- END OF REFERENCE SCHEMA
-- =========================================================
