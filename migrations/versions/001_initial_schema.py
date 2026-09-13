"""Initial schema with users, categories, products, addresses, cart, wishlist, orders, and tokens

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-02

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Pgcrypto extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # 2. Users Table
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(150) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role VARCHAR(30) NOT NULL DEFAULT 'customer' CHECK (role IN ('customer', 'admin')),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
        CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);
        CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at DESC);
    """)

    # 3. Refresh Tokens Table
    op.execute("""
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash VARCHAR(255) UNIQUE NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            revoked BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens (user_id);
        CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token_hash ON refresh_tokens (token_hash);
    """)

    # 4. Categories Table
    op.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(150) UNIQUE NOT NULL,
            description TEXT,
            image_url TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_categories_name ON categories (name);
    """)

    # 5. Products Table
    op.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            main_image_url TEXT NOT NULL,
            other_image_urls TEXT[] DEFAULT '{}',
            price NUMERIC(12, 2) NOT NULL CHECK (price >= 0),
            category_id UUID NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
            description TEXT,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_products_category_id ON products (category_id);
        CREATE INDEX IF NOT EXISTS idx_products_is_active ON products (is_active);
        CREATE INDEX IF NOT EXISTS idx_products_created_at ON products (created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_products_price ON products (price);
        CREATE INDEX IF NOT EXISTS idx_products_name ON products (name);
        CREATE INDEX IF NOT EXISTS idx_products_active_category ON products (is_active, category_id);
    """)

    # 6. User Addresses Table
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_addresses (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            full_name VARCHAR(150) NOT NULL,
            phone VARCHAR(30) NOT NULL,
            address_line_1 TEXT NOT NULL,
            address_line_2 TEXT,
            city VARCHAR(100) NOT NULL,
            state VARCHAR(100) NOT NULL,
            postal_code VARCHAR(20) NOT NULL,
            country VARCHAR(100) NOT NULL DEFAULT 'India',
            is_default BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_user_addresses_user_id ON user_addresses (user_id);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_user_addresses_unique_default 
            ON user_addresses (user_id) 
            WHERE is_default = TRUE;
    """)

    # 7. Carts & Cart Items Table
    op.execute("""
        CREATE TABLE IF NOT EXISTS carts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS cart_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cart_id UUID NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
            product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_cart_items_cart_product UNIQUE (cart_id, product_id)
        );
        CREATE INDEX IF NOT EXISTS idx_cart_items_cart_id ON cart_items (cart_id);
        CREATE INDEX IF NOT EXISTS idx_cart_items_product_id ON cart_items (product_id);
    """)

    # 8. Wishlist Items Table
    op.execute("""
        CREATE TABLE IF NOT EXISTS wishlist_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_wishlist_items_user_product UNIQUE (user_id, product_id)
        );
        CREATE INDEX IF NOT EXISTS idx_wishlist_items_user_id ON wishlist_items (user_id);
        CREATE INDEX IF NOT EXISTS idx_wishlist_items_product_id ON wishlist_items (product_id);
    """)

    # 9. Orders & Order Items Table
    op.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            address_id UUID REFERENCES user_addresses(id) ON DELETE SET NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled')),
            payment_status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (payment_status IN ('pending', 'paid', 'failed', 'refunded')),
            payment_method VARCHAR(50) NOT NULL,
            subtotal NUMERIC(12, 2) NOT NULL CHECK (subtotal >= 0),
            discount NUMERIC(12, 2) NOT NULL DEFAULT 0.00 CHECK (discount >= 0),
            shipping_fee NUMERIC(12, 2) NOT NULL DEFAULT 0.00 CHECK (shipping_fee >= 0),
            total_amount NUMERIC(12, 2) NOT NULL CHECK (total_amount >= 0),
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders (user_id);
        CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status);
        CREATE INDEX IF NOT EXISTS idx_orders_payment_status ON orders (payment_status);
        CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders (created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_orders_analytics_revenue ON orders (status, payment_status, created_at);

        CREATE TABLE IF NOT EXISTS order_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            product_id UUID REFERENCES products(id) ON DELETE SET NULL,
            product_name VARCHAR(255) NOT NULL,
            product_image_url TEXT,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0),
            subtotal NUMERIC(12, 2) NOT NULL CHECK (subtotal >= 0)
        );
        CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items (order_id);
        CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items (product_id);
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS order_items CASCADE;
        DROP TABLE IF EXISTS orders CASCADE;
        DROP TABLE IF EXISTS wishlist_items CASCADE;
        DROP TABLE IF EXISTS cart_items CASCADE;
        DROP TABLE IF EXISTS carts CASCADE;
        DROP TABLE IF EXISTS user_addresses CASCADE;
        DROP TABLE IF EXISTS products CASCADE;
        DROP TABLE IF EXISTS categories CASCADE;
        DROP TABLE IF EXISTS refresh_tokens CASCADE;
        DROP TABLE IF EXISTS users CASCADE;
    """)
