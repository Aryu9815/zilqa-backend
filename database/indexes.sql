-- =============================================================================
-- E-Commerce PostgreSQL Performance & Foreign Key Indexes
-- =============================================================================

-- Users Indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users (google_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at DESC);

-- Refresh Tokens Indexes
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens (user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token_hash ON refresh_tokens (token_hash);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at ON refresh_tokens (expires_at);

-- Categories Indexes
CREATE INDEX IF NOT EXISTS idx_categories_name ON categories (name);
CREATE INDEX IF NOT EXISTS idx_categories_is_deleted ON categories (is_deleted);

-- Products Indexes
CREATE INDEX IF NOT EXISTS idx_products_category_ids ON products USING GIN (category_ids);
CREATE INDEX IF NOT EXISTS idx_products_related_ids ON products USING GIN (related_product_ids);
CREATE INDEX IF NOT EXISTS idx_products_is_active ON products (is_active);
CREATE INDEX IF NOT EXISTS idx_products_is_active_deleted ON products (is_active, is_deleted);
CREATE INDEX IF NOT EXISTS idx_products_created_at ON products (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_products_price ON products (price);
CREATE INDEX IF NOT EXISTS idx_products_name ON products (name);

-- User Addresses Indexes
CREATE INDEX IF NOT EXISTS idx_user_addresses_user_id ON user_addresses (user_id);
CREATE INDEX IF NOT EXISTS idx_user_addresses_is_default ON user_addresses (user_id, is_default);

-- Carts & Cart Items Indexes
CREATE INDEX IF NOT EXISTS idx_carts_user_id ON carts (user_id);
CREATE INDEX IF NOT EXISTS idx_cart_items_cart_id ON cart_items (cart_id);
CREATE INDEX IF NOT EXISTS idx_cart_items_product_id ON cart_items (product_id);

-- Wishlist Items Indexes
CREATE INDEX IF NOT EXISTS idx_wishlist_items_user_id ON wishlist_items (user_id);
CREATE INDEX IF NOT EXISTS idx_wishlist_items_product_id ON wishlist_items (product_id);

-- Orders Indexes
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders (user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status);
CREATE INDEX IF NOT EXISTS idx_orders_payment_status ON orders (payment_status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_user_created ON orders (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_analytics_revenue ON orders (status, payment_status, created_at);

-- Order Items Indexes
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items (order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items (product_id);

-- Reviews Indexes
CREATE INDEX IF NOT EXISTS idx_reviews_product_id ON reviews (product_id);
CREATE INDEX IF NOT EXISTS idx_reviews_user_id ON reviews (user_id);
CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews (rating);
CREATE INDEX IF NOT EXISTS idx_reviews_product_active ON reviews (product_id, is_active, is_deleted);
CREATE INDEX IF NOT EXISTS idx_reviews_created_at ON reviews (created_at DESC);

-- Countries Indexes
CREATE INDEX IF NOT EXISTS idx_countries_name ON countries (name);
CREATE INDEX IF NOT EXISTS idx_countries_code ON countries (code);
CREATE INDEX IF NOT EXISTS idx_countries_is_active ON countries (is_active, is_deleted);
