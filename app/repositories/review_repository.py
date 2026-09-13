from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
import asyncpg
from app.repositories.base_repository import BaseRepository
from app.schemas.review import ReviewCreate, ReviewSortBy, ReviewUpdate


class ReviewRepository(BaseRepository):

    async def get_by_id(
        self,
        review_id: UUID,
        is_active_only: bool = False,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        query = """
            SELECT r.id, r.product_id, r.user_id, u.name AS user_name,
                   p.name AS product_name, p.main_image_url AS product_main_image_url,
                   r.rating, r.comment, r.image_urls,
                   r.is_general, r.is_verified, r.is_active, r.is_deleted,
                   r.created_at, r.updated_at
            FROM reviews r
            LEFT JOIN users u ON r.user_id = u.id
            LEFT JOIN products p ON r.product_id = p.id
            WHERE r.id = $1 AND r.is_deleted = FALSE
        """
        if is_active_only:
            query += " AND r.is_active = TRUE AND (p.id IS NULL OR (p.is_active = TRUE AND p.is_deleted = FALSE))"

        return await self.fetch_one(query, review_id, connection=connection)

    async def list_reviews(
        self,
        page: int = 1,
        limit: int = 20,
        product_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        rating: Optional[int] = None,
        is_general: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        is_active_only: bool = True,
        include_deleted: bool = False,
        sort_by: Optional[ReviewSortBy] = ReviewSortBy.NEWEST,
        connection: Optional[asyncpg.Connection] = None
    ) -> Tuple[List[asyncpg.Record], int]:
        conditions = []
        params: List[Any] = []
        idx = 1

        if not include_deleted:
            conditions.append("r.is_deleted = FALSE")

        if is_active_only:
            conditions.append("r.is_active = TRUE")
            conditions.append("(p.id IS NULL OR (p.is_active = TRUE AND p.is_deleted = FALSE))")

        if product_id is not None:
            conditions.append(f"r.product_id = ${idx}")
            params.append(product_id)
            idx += 1

        if user_id is not None:
            conditions.append(f"r.user_id = ${idx}")
            params.append(user_id)
            idx += 1

        if rating is not None:
            conditions.append(f"r.rating = ${idx}")
            params.append(rating)
            idx += 1

        if is_general is not None:
            conditions.append(f"r.is_general = ${idx}")
            params.append(is_general)
            idx += 1

        if is_verified is not None:
            conditions.append(f"r.is_verified = ${idx}")
            params.append(is_verified)
            idx += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Count query
        count_query = f"""
            SELECT COUNT(*)
            FROM reviews r
            LEFT JOIN products p ON r.product_id = p.id
            {where_clause}
        """
        total = await self.fetch_val(count_query, *params, connection=connection) or 0

        # Sort order
        order_by = "r.created_at DESC"
        if sort_by == ReviewSortBy.OLDEST:
            order_by = "r.created_at ASC"
        elif sort_by == ReviewSortBy.HIGHEST_RATING:
            order_by = "r.rating DESC, r.created_at DESC"
        elif sort_by == ReviewSortBy.LOWEST_RATING:
            order_by = "r.rating ASC, r.created_at DESC"

        offset = (page - 1) * limit
        params.extend([limit, offset])

        query = f"""
            SELECT r.id, r.product_id, r.user_id, u.name AS user_name,
                   p.name AS product_name, p.main_image_url AS product_main_image_url,
                   r.rating, r.comment, r.image_urls,
                   r.is_general, r.is_verified, r.is_active, r.is_deleted,
                   r.created_at, r.updated_at
            FROM reviews r
            LEFT JOIN users u ON r.user_id = u.id
            LEFT JOIN products p ON r.product_id = p.id
            {where_clause}
            ORDER BY {order_by}
            LIMIT ${idx} OFFSET ${idx + 1}
        """
        records = await self.fetch_all(query, *params, connection=connection)
        return records, total

    async def get_product_summary(
        self,
        product_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> Dict[str, Any]:
        query = """
            SELECT
                COUNT(*) AS total_reviews,
                COALESCE(ROUND(AVG(rating)::numeric, 2), 0.0) AS average_rating,
                COUNT(*) FILTER (WHERE rating = 1) AS stars_1,
                COUNT(*) FILTER (WHERE rating = 2) AS stars_2,
                COUNT(*) FILTER (WHERE rating = 3) AS stars_3,
                COUNT(*) FILTER (WHERE rating = 4) AS stars_4,
                COUNT(*) FILTER (WHERE rating = 5) AS stars_5
            FROM reviews
            WHERE product_id = $1 AND is_active = TRUE AND is_deleted = FALSE
        """
        record = await self.fetch_one(query, product_id, connection=connection)
        if not record:
            return {
                "product_id": product_id,
                "average_rating": 0.0,
                "total_reviews": 0,
                "rating_breakdown": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            }

        return {
            "product_id": product_id,
            "average_rating": float(record["average_rating"]),
            "total_reviews": int(record["total_reviews"]),
            "rating_breakdown": {
                1: int(record["stars_1"]),
                2: int(record["stars_2"]),
                3: int(record["stars_3"]),
                4: int(record["stars_4"]),
                5: int(record["stars_5"])
            }
        }

    async def check_user_purchased_product(
        self,
        user_id: UUID,
        product_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> bool:
        query = """
            SELECT EXISTS (
                SELECT 1
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                WHERE o.user_id = $1
                  AND oi.product_id = $2
                  AND o.status NOT IN ('cancelled')
                  AND o.payment_status = 'paid'
            )
        """
        val = await self.fetch_val(query, user_id, product_id, connection=connection)
        return bool(val)

    async def create(
        self,
        review_in: ReviewCreate,
        user_id: Optional[UUID] = None,
        is_verified: bool = False,
        connection: Optional[asyncpg.Connection] = None
    ) -> asyncpg.Record:
        query = """
            INSERT INTO reviews (
                product_id, user_id, rating, comment, image_urls,
                is_general, is_verified, is_active, is_deleted,
                created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id, product_id, user_id, rating, comment, image_urls,
                      is_general, is_verified, is_active, is_deleted,
                      created_at, updated_at
        """
        record = await self.fetch_one(
            query,
            review_in.product_id,
            user_id,
            review_in.rating,
            review_in.comment,
            review_in.image_urls,
            review_in.is_general,
            is_verified,
            connection=connection
        )
        assert record is not None
        return record

    async def update(
        self,
        review_id: UUID,
        review_in: ReviewUpdate,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        updates = []
        params: List[Any] = []
        idx = 1

        fields = [
            ("rating", review_in.rating),
            ("comment", review_in.comment),
            ("image_urls", review_in.image_urls),
            ("is_general", review_in.is_general),
        ]

        for col, val in fields:
            if val is not None:
                updates.append(f"{col} = ${idx}")
                params.append(val)
                idx += 1

        if not updates:
            return await self.get_by_id(review_id, connection=connection)

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(review_id)

        query = f"""
            UPDATE reviews
            SET {", ".join(updates)}
            WHERE id = ${idx} AND is_deleted = FALSE
            RETURNING id, product_id, user_id, rating, comment, image_urls,
                      is_general, is_verified, is_active, is_deleted,
                      created_at, updated_at
        """
        return await self.fetch_one(query, *params, connection=connection)

    async def update_status(
        self,
        review_id: UUID,
        is_active: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        updates = []
        params: List[Any] = []
        idx = 1

        if is_active is not None:
            updates.append(f"is_active = ${idx}")
            params.append(is_active)
            idx += 1

        if is_verified is not None:
            updates.append(f"is_verified = ${idx}")
            params.append(is_verified)
            idx += 1

        if not updates:
            return await self.get_by_id(review_id, connection=connection)

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(review_id)

        query = f"""
            UPDATE reviews
            SET {", ".join(updates)}
            WHERE id = ${idx}
            RETURNING id, product_id, user_id, rating, comment, image_urls,
                      is_general, is_verified, is_active, is_deleted,
                      created_at, updated_at
        """
        return await self.fetch_one(query, *params, connection=connection)

    async def delete(
        self,
        review_id: UUID,
        soft: bool = True,
        connection: Optional[asyncpg.Connection] = None
    ) -> bool:
        if soft:
            query = """
                UPDATE reviews
                SET is_deleted = TRUE, is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
                RETURNING id
            """
        else:
            query = "DELETE FROM reviews WHERE id = $1 RETURNING id"

        res = await self.fetch_one(query, review_id, connection=connection)
        return res is not None


review_repository = ReviewRepository()
