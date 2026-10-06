"""Seed runner script to populate database with initial admin user, categories, and sample products."""
import asyncio
import logging
import os
import sys

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from uuid import UUID
import asyncpg
from app.core.config import settings
from app.core.security import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed")


async def seed_database() -> None:
    logger.info(f"Connecting to database at {settings.DATABASE_URL}...")
    conn = await asyncpg.connect(settings.DATABASE_URL)
    
    try:
        async with conn.transaction():
            # 1. Seed Admin User
            admin_email = "admin@example.com"
            admin_pwd = "Admin@123"
            admin_hash = hash_password(admin_pwd)

            logger.info("Seeding Admin user (admin@example.com / Admin@123)...")
            await conn.execute(
                """
                INSERT INTO admins (id, name, email, password_hash, is_active, created_at, updated_at)
                VALUES (
                    'a0000000-0000-0000-0000-000000000001',
                    'System Administrator',
                    LOWER($1),
                    $2,
                    TRUE,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT (email) DO UPDATE
                SET password_hash = EXCLUDED.password_hash,
                    is_active = TRUE,
                    updated_at = CURRENT_TIMESTAMP;
                """,
                admin_email,
                admin_hash
            )

            # 2. Seed Customer User
            cust_email = "customer@example.com"
            cust_pwd = "Customer@123"
            cust_hash = hash_password(cust_pwd)

            logger.info("Seeding Customer user (customer@example.com / Customer@123)...")
            await conn.execute(
                """
                INSERT INTO users (id, name, email, password_hash, is_active, created_at, updated_at)
                VALUES (
                    'a0000000-0000-0000-0000-000000000002',
                    'John Doe',
                    LOWER($1),
                    $2,
                    TRUE,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT (email) DO NOTHING;
                """,
                cust_email,
                cust_hash
            )

            # 3. Seed Categories
            logger.info("Seeding sample categories...")
            categories = [
                (
                    'c0000000-0000-0000-0000-000000000001',
                    'Rings',
                    'Exquisite silver, gold, and gemstone rings crafted for every occasion.',
                    'https://images.unsplash.com/photo-1605100804763-247f67b3557e?auto=format&fit=crop&w=800&q=80'
                ),
                (
                    'c0000000-0000-0000-0000-000000000002',
                    'Necklaces & Pendants',
                    'Elegant pendants and timeless necklaces crafted with precision.',
                    'https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?auto=format&fit=crop&w=800&q=80'
                ),
                (
                    'c0000000-0000-0000-0000-000000000003',
                    'Bracelets & Bangles',
                    'Contemporary and traditional bracelets designed to stand out.',
                    'https://images.unsplash.com/photo-1611591475878-3c321faebf90?auto=format&fit=crop&w=800&q=80'
                ),
                (
                    'c0000000-0000-0000-0000-000000000004',
                    'Earrings',
                    'Stunning studs, drops, and hoops for classic and modern styling.',
                    'https://images.unsplash.com/photo-1630019852942-f89202989a59?auto=format&fit=crop&w=800&q=80'
                )
            ]
            for cat_id, cat_name, cat_desc, cat_img in categories:
                await conn.execute(
                    """
                    INSERT INTO categories (id, name, description, image_url, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (name) DO UPDATE
                    SET description = EXCLUDED.description,
                        image_url = EXCLUDED.image_url,
                        updated_at = CURRENT_TIMESTAMP;
                    """,
                    cat_id, cat_name, cat_desc, cat_img
                )

            # 4. Seed Products
            logger.info("Seeding sample products...")
            products = [
                (
                    'd0000000-0000-0000-0000-000000000001',
                    'India Flag Ring',
                    'https://images.unsplash.com/photo-1605100804763-247f67b3557e?auto=format&fit=crop&w=800&q=80',
                    ['https://images.unsplash.com/photo-1603561591411-07134e71a2a9?auto=format&fit=crop&w=800&q=80'],
                    999.00,
                    [UUID('c0000000-0000-0000-0000-000000000001')],
                    'Premium 925 Sterling Silver tricolor tri-band ring inspired by India.'
                ),
                (
                    'd0000000-0000-0000-0000-000000000002',
                    'Silver Lotus Pendant',
                    'https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?auto=format&fit=crop&w=800&q=80',
                    ['https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?auto=format&fit=crop&w=800&q=80'],
                    1499.00,
                    [UUID('c0000000-0000-0000-0000-000000000002')],
                    'Handcrafted sterling silver lotus flower necklace with fine link chain.'
                ),
                (
                    'd0000000-0000-0000-0000-000000000003',
                    'Royal Peacock Bracelet',
                    'https://images.unsplash.com/photo-1611591475878-3c321faebf90?auto=format&fit=crop&w=800&q=80',
                    ['https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?auto=format&fit=crop&w=800&q=80'],
                    2499.00,
                    [UUID('c0000000-0000-0000-0000-000000000003')],
                    'Intricate peacock motif bracelet adorned with synthetic emeralds and zircon.'
                ),
                (
                    'd0000000-0000-0000-0000-000000000004',
                    'Pearl Drop Earrings',
                    'https://images.unsplash.com/photo-1630019852942-f89202989a59?auto=format&fit=crop&w=800&q=80',
                    ['https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?auto=format&fit=crop&w=800&q=80'],
                    899.00,
                    [UUID('c0000000-0000-0000-0000-000000000004')],
                    'Freshwater cultured pearls hanging from hypoallergenic silver hooks.'
                ),
                (
                    'd0000000-0000-0000-0000-000000000005',
                    'Diamond Solitaire Ring',
                    'https://images.unsplash.com/photo-1603561591411-07134e71a2a9?auto=format&fit=crop&w=800&q=80',
                    ['https://images.unsplash.com/photo-1605100804763-247f67b3557e?auto=format&fit=crop&w=800&q=80'],
                    4999.00,
                    [UUID('c0000000-0000-0000-0000-000000000001')],
                    'Brilliant round-cut moissanite solitaire ring in 14K white gold finish.'
                )
            ]
            for p_id, p_name, p_main_img, p_other_imgs, p_price, p_cat_ids, p_desc in products:
                await conn.execute(
                    """
                    INSERT INTO products (id, name, main_image_url, other_image_urls, price, category_ids, description, is_active, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (id) DO UPDATE
                    SET name = EXCLUDED.name,
                        main_image_url = EXCLUDED.main_image_url,
                        price = EXCLUDED.price,
                        category_ids = EXCLUDED.category_ids,
                        updated_at = CURRENT_TIMESTAMP;
                    """,
                    p_id, p_name, p_main_img, p_other_imgs, p_price, p_cat_ids, p_desc
                )

            # 5. Seed Reviews
            logger.info("Seeding sample reviews (general testimonials and product reviews)...")
            reviews = [
                # General Client Reviews (Testimonials for Home page)
                (
                    'e0000000-0000-0000-0000-000000000001',
                    'd0000000-0000-0000-0000-000000000001',
                    'a0000000-0000-0000-0000-000000000002',
                    5,
                    "The weight and finish of the Eternity Band are exquisite. It has become a staple in my daily wardrobe. Truly exceptional craftsmanship.",
                    ['https://images.unsplash.com/photo-1605100804763-247f67b3557e?auto=format&fit=crop&w=800&q=80'],
                    True,   # is_general
                    True,   # is_verified
                ),
                (
                    'e0000000-0000-0000-0000-000000000002',
                    'd0000000-0000-0000-0000-000000000002',
                    'a0000000-0000-0000-0000-000000000002',
                    5,
                    "I was searching for minimal silver pieces that didn't feel cheap. zelqa delivered perfectly. The packaging alone felt incredibly luxurious.",
                    ['https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?auto=format&fit=crop&w=800&q=80'],
                    True,   # is_general
                    True,   # is_verified
                ),
                (
                    'e0000000-0000-0000-0000-000000000003',
                    'd0000000-0000-0000-0000-000000000003',
                    'a0000000-0000-0000-0000-000000000002',
                    5,
                    "Beautifully understated. The Link Chain bracelet pairs with everything I own. Customer service was also very responsive regarding sizing.",
                    ['https://images.unsplash.com/photo-1611591475878-3c321faebf90?auto=format&fit=crop&w=800&q=80'],
                    True,   # is_general
                    True,   # is_verified
                ),
                # Specific Product Reviews
                (
                    'e0000000-0000-0000-0000-000000000004',
                    'd0000000-0000-0000-0000-000000000001',
                    'a0000000-0000-0000-0000-000000000002',
                    5,
                    "Exceeded my expectations entirely! The weight and polished finish feel incredibly luxurious. The vertical gallery was also very cool to see.",
                    [],
                    False,  # is_general
                    True,   # is_verified
                ),
                (
                    'e0000000-0000-0000-0000-000000000005',
                    'd0000000-0000-0000-0000-000000000001',
                    'a0000000-0000-0000-0000-000000000002',
                    5,
                    "Solid, sturdy, and doesn't irritate my sensitive skin at all. I wear it every day and it still shines brilliantly.",
                    [],
                    False,
                    True,
                ),
                (
                    'e0000000-0000-0000-0000-000000000006',
                    'd0000000-0000-0000-0000-000000000001',
                    'a0000000-0000-0000-0000-000000000002',
                    4,
                    "Stunning finish and great minimalist packaging. The mirror shine is outstanding.",
                    [],
                    False,
                    True,
                )
            ]
            for r_id, r_prod_id, r_user_id, r_rating, r_comment, r_imgs, r_general, r_verified in reviews:
                # Check if product exists before inserting
                prod_exists = await conn.fetchval("SELECT id FROM products WHERE id = $1", r_prod_id)
                if not prod_exists:
                    # Pick any existing product
                    any_prod_id = await conn.fetchval("SELECT id FROM products LIMIT 1")
                    if any_prod_id:
                        r_prod_id = any_prod_id
                    else:
                        continue

                await conn.execute(
                    """
                    INSERT INTO reviews (id, product_id, user_id, rating, comment, image_urls, is_general, is_verified, is_active, is_deleted, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, TRUE, FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (id) DO UPDATE
                    SET comment = EXCLUDED.comment,
                        rating = EXCLUDED.rating,
                        is_general = EXCLUDED.is_general,
                        is_verified = EXCLUDED.is_verified,
                        updated_at = CURRENT_TIMESTAMP;
                    """,
                    r_id, r_prod_id, r_user_id, r_rating, r_comment, r_imgs, r_general, r_verified
                )

        logger.info("Database seeding completed successfully!")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed_database())
