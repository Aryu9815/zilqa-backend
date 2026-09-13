-- =============================================================================
-- E-Commerce PostgreSQL Integrity & Business Rule Constraints
-- =============================================================================

-- Users Constraints
ALTER TABLE users 
    DROP CONSTRAINT IF EXISTS chk_users_role,
    ADD CONSTRAINT chk_users_role CHECK (role IN ('customer', 'admin'));

-- Products Constraints
ALTER TABLE products 
    DROP CONSTRAINT IF EXISTS chk_products_price,
    ADD CONSTRAINT chk_products_price CHECK (price >= 0);

-- Cart Items Constraints
ALTER TABLE cart_items 
    DROP CONSTRAINT IF EXISTS uq_cart_items_cart_product,
    ADD CONSTRAINT uq_cart_items_cart_product UNIQUE (cart_id, product_id);

ALTER TABLE cart_items 
    DROP CONSTRAINT IF EXISTS chk_cart_items_quantity,
    ADD CONSTRAINT chk_cart_items_quantity CHECK (quantity > 0);

-- Wishlist Items Constraints
ALTER TABLE wishlist_items 
    DROP CONSTRAINT IF EXISTS uq_wishlist_items_user_product,
    ADD CONSTRAINT uq_wishlist_items_user_product UNIQUE (user_id, product_id);

-- User Addresses Constraints: Enforce single default address per user
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_addresses_unique_default 
    ON user_addresses (user_id) 
    WHERE is_default = TRUE;

-- Orders Constraints
ALTER TABLE orders 
    DROP CONSTRAINT IF EXISTS chk_orders_subtotal,
    ADD CONSTRAINT chk_orders_subtotal CHECK (subtotal >= 0);

ALTER TABLE orders 
    DROP CONSTRAINT IF EXISTS chk_orders_discount,
    ADD CONSTRAINT chk_orders_discount CHECK (discount >= 0);

ALTER TABLE orders 
    DROP CONSTRAINT IF EXISTS chk_orders_shipping_fee,
    ADD CONSTRAINT chk_orders_shipping_fee CHECK (shipping_fee >= 0);

ALTER TABLE orders 
    DROP CONSTRAINT IF EXISTS chk_orders_total_amount,
    ADD CONSTRAINT chk_orders_total_amount CHECK (total_amount >= 0);

ALTER TABLE orders 
    DROP CONSTRAINT IF EXISTS chk_orders_status,
    ADD CONSTRAINT chk_orders_status CHECK (status IN ('pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled'));

ALTER TABLE orders 
    DROP CONSTRAINT IF EXISTS chk_orders_payment_status,
    ADD CONSTRAINT chk_orders_payment_status CHECK (payment_status IN ('pending', 'paid', 'failed', 'refunded'));

-- Order Items Constraints
ALTER TABLE order_items 
    DROP CONSTRAINT IF EXISTS chk_order_items_quantity,
    ADD CONSTRAINT chk_order_items_quantity CHECK (quantity > 0);

ALTER TABLE order_items 
    DROP CONSTRAINT IF EXISTS chk_order_items_unit_price,
    ADD CONSTRAINT chk_order_items_unit_price CHECK (unit_price >= 0);

ALTER TABLE order_items 
    DROP CONSTRAINT IF EXISTS chk_order_items_subtotal,
    ADD CONSTRAINT chk_order_items_subtotal CHECK (subtotal >= 0);
