import json
from decimal import Decimal
from typing import Any, List, Optional, Tuple
from uuid import UUID
import asyncpg

from app.repositories.base_repository import BaseRepository
from app.schemas.product import ProductCreate, ProductSortBy, ProductUpdate


class ProductRepository(BaseRepository):

    async def get_by_id(
        self,
        product_id: UUID,
        is_active_only: bool = True,
        include_deleted: bool = False,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        conditions = ["p.id = $1"]
        if not include_deleted:
            conditions.append("p.is_deleted = FALSE")
        if is_active_only:
            conditions.append("p.is_active = TRUE")

        query = f"""
            SELECT p.id, p.name, p.main_image_url, p.other_image_urls, p.price,
                   p.category_ids,
                   COALESCE(
                       ARRAY(
                           SELECT c.name
                           FROM categories c
                           WHERE c.id = ANY(p.category_ids) AND c.is_deleted = FALSE
                           ORDER BY c.priority ASC, c.name ASC
                       ),
                       '{{}}'::text[]
                   ) AS category_names,
                   p.description,
                   p.related_product_ids,
                   p.product_description,
                   p.faqs,
                   p.is_active, p.created_at, p.updated_at
            FROM products p
            WHERE {" AND ".join(conditions)}
        """
        return await self.fetch_one(query, product_id, connection=connection)

    async def get_by_ids(
        self,
        product_ids: List[UUID],
        is_active_only: bool = True,
        include_deleted: bool = False,
        connection: Optional[asyncpg.Connection] = None
    ) -> List[asyncpg.Record]:
        if not product_ids:
            return []
        conditions = ["p.id = ANY($1)"]
        if not include_deleted:
            conditions.append("p.is_deleted = FALSE")
        if is_active_only:
            conditions.append("p.is_active = TRUE")

        query = f"""
            SELECT p.id, p.name, p.main_image_url, p.other_image_urls, p.price,
                   p.category_ids,
                   COALESCE(
                       ARRAY(
                           SELECT c.name
                           FROM categories c
                           WHERE c.id = ANY(p.category_ids) AND c.is_deleted = FALSE
                           ORDER BY c.priority ASC, c.name ASC
                       ),
                       '{{}}'::text[]
                   ) AS category_names,
                   p.description,
                   p.related_product_ids,
                   p.product_description,
                   p.faqs,
                   p.is_active, p.created_at, p.updated_at
            FROM products p
            WHERE {" AND ".join(conditions)}
            ORDER BY p.name ASC
        """
        return await self.fetch_all(query, product_ids, connection=connection)

    async def list_products(
        self,
        page: int = 1,
        limit: int = 20,
        category_id: Optional[UUID] = None,
        category_ids: Optional[List[UUID]] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        search: Optional[str] = None,
        sort_by: Optional[ProductSortBy] = ProductSortBy.NEWEST,
        is_active_only: bool = True,
        include_deleted: bool = False,
        connection: Optional[asyncpg.Connection] = None
    ) -> Tuple[List[asyncpg.Record], int]:
        conditions = []
        params: List[Any] = []
        idx = 1

        if not include_deleted:
            conditions.append("p.is_deleted = FALSE")

        if is_active_only:
            conditions.append("p.is_active = TRUE")

        if category_id is not None:
            conditions.append(f"${idx} = ANY(p.category_ids)")
            params.append(category_id)
            idx += 1

        if category_ids:
            conditions.append(f"p.category_ids && ${idx}::uuid[]")
            params.append(category_ids)
            idx += 1

        if min_price is not None:
            conditions.append(f"p.price >= ${idx}")
            params.append(min_price)
            idx += 1

        if max_price is not None:
            conditions.append(f"p.price <= ${idx}")
            params.append(max_price)
            idx += 1

        if search:
            search_pattern = f"%{search.strip()}%"
            conditions.append(f"(p.name ILIKE ${idx} OR p.description ILIKE ${idx} OR p.product_description ILIKE ${idx})")
            params.append(search_pattern)
            idx += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Count total
        count_query = f"""
            SELECT COUNT(*) 
            FROM products p 
            {where_clause}
        """
        total = await self.fetch_val(count_query, *params, connection=connection) or 0

        # Sort Order
        order_by = "p.created_at DESC"
        if sort_by == ProductSortBy.PRICE_ASC:
            order_by = "p.price ASC"
        elif sort_by == ProductSortBy.PRICE_DESC:
            order_by = "p.price DESC"
        elif sort_by == ProductSortBy.OLDEST:
            order_by = "p.created_at ASC"
        elif sort_by == ProductSortBy.NAME_ASC:
            order_by = "p.name ASC"
        elif sort_by == ProductSortBy.NAME_DESC:
            order_by = "p.name DESC"

        offset = (page - 1) * limit
        params.extend([limit, offset])

        query = f"""
            SELECT p.id, p.name, p.main_image_url, p.other_image_urls, p.price,
                   p.category_ids,
                   COALESCE(
                       ARRAY(
                           SELECT c.name
                           FROM categories c
                           WHERE c.id = ANY(p.category_ids) AND c.is_deleted = FALSE
                           ORDER BY c.priority ASC, c.name ASC
                       ),
                       '{{}}'::text[]
                   ) AS category_names,
                   p.description,
                   p.related_product_ids,
                   p.product_description,
                   p.faqs,
                   p.is_active, p.created_at, p.updated_at
            FROM products p
            {where_clause}
            ORDER BY {order_by}
            LIMIT ${idx} OFFSET ${idx + 1}
        """
        records = await self.fetch_all(query, *params, connection=connection)
        return records, total

    async def create(
        self,
        product_in: ProductCreate,
        connection: Optional[asyncpg.Connection] = None
    ) -> asyncpg.Record:
        faqs_json = json.dumps([
            f.model_dump() if hasattr(f, "model_dump") else dict(f)
            for f in (product_in.faqs or [])
        ])

        query = """
            INSERT INTO products (
                name, main_image_url, other_image_urls, price,
                category_ids, description, related_product_ids, product_description, faqs,
                is_active, is_deleted, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10, FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id, name, main_image_url, other_image_urls, price,
                      category_ids, description, related_product_ids, product_description, faqs,
                      is_active, created_at, updated_at
        """
        record = await self.fetch_one(
            query,
            product_in.name,
            product_in.main_image_url,
            product_in.other_image_urls,
            product_in.price,
            product_in.category_ids,
            product_in.description,
            product_in.related_product_ids,
            product_in.product_description,
            faqs_json,
            product_in.is_active,
            connection=connection
        )
        assert record is not None
        return record

    async def update(
        self,
        product_id: UUID,
        product_in: ProductUpdate,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        updates = []
        params: List[Any] = []
        idx = 1

        fields = [
            ("name", product_in.name),
            ("main_image_url", product_in.main_image_url),
            ("other_image_urls", product_in.other_image_urls),
            ("price", product_in.price),
            ("category_ids", product_in.category_ids),
            ("description", product_in.description),
            ("related_product_ids", product_in.related_product_ids),
            ("product_description", product_in.product_description),
            ("is_active", product_in.is_active),
        ]

        for col, val in fields:
            if val is not None:
                updates.append(f"{col} = ${idx}")
                params.append(val)
                idx += 1

        if product_in.faqs is not None:
            faqs_json = json.dumps([
                f.model_dump() if hasattr(f, "model_dump") else dict(f)
                for f in product_in.faqs
            ])
            updates.append(f"faqs = ${idx}::jsonb")
            params.append(faqs_json)
            idx += 1

        if not updates:
            return await self.get_by_id(product_id, is_active_only=False, include_deleted=False, connection=connection)

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(product_id)

        query = f"""
            UPDATE products
            SET {", ".join(updates)}
            WHERE id = ${idx} AND is_deleted = FALSE
            RETURNING id, name, main_image_url, other_image_urls, price,
                      category_ids, description, related_product_ids, product_description, faqs,
                      is_active, created_at, updated_at
        """
        return await self.fetch_one(query, *params, connection=connection)

    async def delete(
        self,
        product_id: UUID,
        soft: bool = True,
        connection: Optional[asyncpg.Connection] = None
    ) -> bool:
        if soft:
            query = """
                UPDATE products
                SET is_deleted = TRUE, is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1 AND is_deleted = FALSE
                RETURNING id
            """
        else:
            query = "DELETE FROM products WHERE id = $1 RETURNING id"
        res = await self.fetch_one(query, product_id, connection=connection)
        return res is not None


product_repository = ProductRepository()
