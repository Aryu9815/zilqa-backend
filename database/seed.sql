-- =============================================================================
-- E-Commerce Sample Seed Data
-- =============================================================================

-- 1. SEED USERS
-- Default Admin: admin@example.com / Admin@123
-- Default Customer: customer@example.com / Customer@123
-- (Hashes created with Argon2 / Bcrypt)
INSERT INTO users (id, name, email, password_hash, role, is_active, created_at, updated_at)
VALUES 
    (
        'a0000000-0000-0000-0000-000000000001',
        'System Administrator',
        'admin@example.com',
        '$argon2id$v=19$m=65536,t=3,p=4$vUaZ+M3iJp5gLz6kY8uV7w$k+1u8R8w7k9y2q3x4z5t6u7v8w9a0b1c2d3e4f5g6h7',
        'admin',
        TRUE,
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    ),
    (
        'a0000000-0000-0000-0000-000000000002',
        'John Doe',
        'customer@example.com',
        '$argon2id$v=19$m=65536,t=3,p=4$vUaZ+M3iJp5gLz6kY8uV7w$k+1u8R8w7k9y2q3x4z5t6u7v8w9a0b1c2d3e4f5g6h7',
        'customer',
        TRUE,
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    )
ON CONFLICT (email) DO NOTHING;

-- 2. SEED CATEGORIES
INSERT INTO categories (id, name, description, image_url, created_at, updated_at)
VALUES
    (
        'c0000000-0000-0000-0000-000000000001',
        'Rings',
        'Exquisite silver, gold, and gemstone rings crafted for every occasion.',
        'https://images.unsplash.com/photo-1605100804763-247f67b3557e?auto=format&fit=crop&w=800&q=80',
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    ),
    (
        'c0000000-0000-0000-0000-000000000002',
        'Necklaces & Pendants',
        'Elegant pendants and timeless necklaces crafted with precision.',
        'https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?auto=format&fit=crop&w=800&q=80',
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    ),
    (
        'c0000000-0000-0000-0000-000000000003',
        'Bracelets & Bangles',
        'Contemporary and traditional bracelets designed to stand out.',
        'https://images.unsplash.com/photo-1611591475878-3c321faebf90?auto=format&fit=crop&w=800&q=80',
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    ),
    (
        'c0000000-0000-0000-0000-000000000004',
        'Earrings',
        'Stunning studs, drops, and hoops for classic and modern styling.',
        'https://images.unsplash.com/photo-1630019852942-f89202989a59?auto=format&fit=crop&w=800&q=80',
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    )
ON CONFLICT (name) DO NOTHING;

-- 3. SEED PRODUCTS
INSERT INTO products (id, name, main_image_url, other_image_urls, price, category_ids, description, is_active, created_at, updated_at)
VALUES
    (
        'p0000000-0000-0000-0000-000000000001',
        'India Flag Ring',
        'https://images.unsplash.com/photo-1605100804763-247f67b3557e?auto=format&fit=crop&w=800&q=80',
        ARRAY['https://images.unsplash.com/photo-1603561591411-07134e71a2a9?auto=format&fit=crop&w=800&q=80'],
        999.00,
        ARRAY['c0000000-0000-0000-0000-000000000001']::UUID[],
        'Premium 925 Sterling Silver tricolor tri-band ring inspired by India.',
        TRUE,
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    ),
    (
        'p0000000-0000-0000-0000-000000000002',
        'Silver Lotus Pendant',
        'https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?auto=format&fit=crop&w=800&q=80',
        ARRAY['https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?auto=format&fit=crop&w=800&q=80'],
        1499.00,
        ARRAY['c0000000-0000-0000-0000-000000000002']::UUID[],
        'Handcrafted sterling silver lotus flower necklace with fine link chain.',
        TRUE,
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    ),
    (
        'p0000000-0000-0000-0000-000000000003',
        'Royal Peacock Bracelet',
        'https://images.unsplash.com/photo-1611591475878-3c321faebf90?auto=format&fit=crop&w=800&q=80',
        ARRAY['https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?auto=format&fit=crop&w=800&q=80'],
        2499.00,
        ARRAY['c0000000-0000-0000-0000-000000000003']::UUID[],
        'Intricate peacock motif bracelet adorned with synthetic emeralds and zircon.',
        TRUE,
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    ),
    (
        'p0000000-0000-0000-0000-000000000004',
        'Pearl Drop Earrings',
        'https://images.unsplash.com/photo-1630019852942-f89202989a59?auto=format&fit=crop&w=800&q=80',
        ARRAY['https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?auto=format&fit=crop&w=800&q=80'],
        899.00,
        ARRAY['c0000000-0000-0000-0000-000000000004']::UUID[],
        'Freshwater cultured pearls hanging from hypoallergenic silver hooks.',
        TRUE,
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    ),
    (
        'p0000000-0000-0000-0000-000000000005',
        'Diamond Solitaire Ring',
        'https://images.unsplash.com/photo-1603561591411-07134e71a2a9?auto=format&fit=crop&w=800&q=80',
        ARRAY['https://images.unsplash.com/photo-1605100804763-247f67b3557e?auto=format&fit=crop&w=800&q=80'],
        4999.00,
        ARRAY['c0000000-0000-0000-0000-000000000001']::UUID[],
        'Brilliant round-cut moissanite solitaire ring in 14K white gold finish.',
        TRUE,
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    )
ON CONFLICT (id) DO NOTHING;
