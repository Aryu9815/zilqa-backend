from typing import List, Optional, Tuple
from uuid import UUID
import asyncpg

from app.repositories.base_repository import BaseRepository
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryRepository(BaseRepository):

    async def get_by_id(
        self,
        category_id: UUID,
        include_deleted: bool = False,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        conditions = ["id = $1"]
        if not include_deleted:
            conditions.append("is_deleted = FALSE")
        query = f"""
            SELECT id, name, description, image_url, created_at, updated_at
            FROM categories
            WHERE {" AND ".join(conditions)}
        """
        return await self.fetch_one(query, category_id, connection=connection)

    async def get_by_ids(
        self,
        category_ids: List[UUID],
        include_deleted: bool = False,
        connection: Optional[asyncpg.Connection] = None
    ) -> List[asyncpg.Record]:
        if not category_ids:
            return []
        conditions = ["id = ANY($1)"]
        if not include_deleted:
            conditions.append("is_deleted = FALSE")
        query = f"""
            SELECT id, name, description, image_url, created_at, updated_at
            FROM categories
            WHERE {" AND ".join(conditions)}
        """
        return await self.fetch_all(query, category_ids, connection=connection)

    async def get_by_name(
        self,
        name: str,
        include_deleted: bool = False,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        conditions = ["LOWER(name) = LOWER($1)"]
        if not include_deleted:
            conditions.append("is_deleted = FALSE")
        query = f"""
            SELECT id, name, description, image_url, created_at, updated_at
            FROM categories
            WHERE {" AND ".join(conditions)}
        """
        return await self.fetch_one(query, name, connection=connection)

    async def list_categories(
        self,
        page: int = 1,
        limit: int = 20,
        include_deleted: bool = False,
        connection: Optional[asyncpg.Connection] = None
    ) -> Tuple[List[asyncpg.Record], int]:
        conditions = []
        if not include_deleted:
            conditions.append("is_deleted = FALSE")
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        offset = (page - 1) * limit
        count_query = f"SELECT COUNT(*) FROM categories {where_clause}"
        total = await self.fetch_val(count_query, connection=connection) or 0

        query = f"""
            SELECT id, name, description, image_url, created_at, updated_at
            FROM categories
            {where_clause}
            ORDER BY priority ASC
            LIMIT $1 OFFSET $2
        """
        records = await self.fetch_all(query, limit, offset, connection=connection)
        return records, total

    async def create(
        self,
        category_in: CategoryCreate,
        connection: Optional[asyncpg.Connection] = None
    ) -> asyncpg.Record:
        query = """
            INSERT INTO categories (name, description, image_url, is_deleted, created_at, updated_at)
            VALUES ($1, $2, $3, FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id, name, description, image_url, created_at, updated_at
        """
        record = await self.fetch_one(
            query,
            category_in.name,
            category_in.description,
            category_in.image_url,
            connection=connection
        )
        assert record is not None
        return record

    async def update(
        self,
        category_id: UUID,
        category_in: CategoryUpdate,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        updates = []
        params = []
        idx = 1

        if category_in.name is not None:
            updates.append(f"name = ${idx}")
            params.append(category_in.name)
            idx += 1
        if category_in.description is not None:
            updates.append(f"description = ${idx}")
            params.append(category_in.description)
            idx += 1
        if category_in.image_url is not None:
            updates.append(f"image_url = ${idx}")
            params.append(category_in.image_url)
            idx += 1

        if not updates:
            return await self.get_by_id(category_id, include_deleted=False, connection=connection)

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(category_id)

        query = f"""
            UPDATE categories
            SET {", ".join(updates)}
            WHERE id = ${idx} AND is_deleted = FALSE
            RETURNING id, name, description, image_url, created_at, updated_at
        """
        return await self.fetch_one(query, *params, connection=connection)

    async def delete(
        self,
        category_id: UUID,
        soft: bool = True,
        connection: Optional[asyncpg.Connection] = None
    ) -> bool:
        if soft:
            query = """
                UPDATE categories
                SET is_deleted = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1 AND is_deleted = FALSE
                RETURNING id
            """
        else:
            query = "DELETE FROM categories WHERE id = $1 RETURNING id"
        res = await self.fetch_one(query, category_id, connection=connection)
        return res is not None


category_repository = CategoryRepository()
