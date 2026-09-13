from typing import List, Optional, Tuple
from uuid import UUID
import asyncpg

from app.repositories.base_repository import BaseRepository
from app.schemas.country import CountryCreate, CountryUpdate


class CountryRepository(BaseRepository):

    async def get_by_id(
        self,
        country_id: UUID,
        is_active_only: bool = False,
        include_deleted: bool = False,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        conditions = ["id = $1"]
        if not include_deleted:
            conditions.append("is_deleted = FALSE")
        if is_active_only:
            conditions.append("is_active = TRUE")

        query = f"""
            SELECT id, name, TRIM(code) AS code, is_active, is_deleted, created_at, updated_at
            FROM countries
            WHERE {" AND ".join(conditions)}
        """
        return await self.fetch_one(query, country_id, connection=connection)

    async def get_by_name(
        self,
        name: str,
        exclude_id: Optional[UUID] = None,
        include_deleted: bool = False,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        conditions = ["LOWER(name) = LOWER($1)"]
        params = [name.strip()]
        idx = 2

        if exclude_id is not None:
            conditions.append(f"id != ${idx}")
            params.append(exclude_id)
            idx += 1

        if not include_deleted:
            conditions.append("is_deleted = FALSE")

        query = f"""
            SELECT id, name, TRIM(code) AS code, is_active, is_deleted, created_at, updated_at
            FROM countries
            WHERE {" AND ".join(conditions)}
        """
        return await self.fetch_one(query, *params, connection=connection)

    async def get_by_code(
        self,
        code: str,
        exclude_id: Optional[UUID] = None,
        include_deleted: bool = False,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        conditions = ["LOWER(TRIM(code)) = LOWER($1)"]
        params = [code.strip()]
        idx = 2

        if exclude_id is not None:
            conditions.append(f"id != ${idx}")
            params.append(exclude_id)
            idx += 1

        if not include_deleted:
            conditions.append("is_deleted = FALSE")

        query = f"""
            SELECT id, name, TRIM(code) AS code, is_active, is_deleted, created_at, updated_at
            FROM countries
            WHERE {" AND ".join(conditions)}
        """
        return await self.fetch_one(query, *params, connection=connection)

    async def list_countries(
        self,
        page: int = 1,
        limit: int = 50,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        include_deleted: bool = False,
        connection: Optional[asyncpg.Connection] = None
    ) -> Tuple[List[asyncpg.Record], int]:
        conditions = []
        params = []
        idx = 1

        if not include_deleted:
            conditions.append("is_deleted = FALSE")

        if is_active is not None:
            conditions.append(f"is_active = ${idx}")
            params.append(is_active)
            idx += 1

        if search:
            search_pattern = f"%{search.strip()}%"
            conditions.append(f"(name ILIKE ${idx} OR TRIM(code) ILIKE ${idx})")
            params.append(search_pattern)
            idx += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        count_query = f"SELECT COUNT(*) FROM countries {where_clause}"
        total = await self.fetch_val(count_query, *params, connection=connection) or 0

        offset = (page - 1) * limit
        data_params = list(params)
        data_params.extend([limit, offset])

        query = f"""
            SELECT id, name, TRIM(code) AS code, is_active, is_deleted, created_at, updated_at
            FROM countries
            {where_clause}
            ORDER BY name ASC
            LIMIT ${idx} OFFSET ${idx + 1}
        """
        records = await self.fetch_all(query, *data_params, connection=connection)
        return records, total

    async def create(
        self,
        country_in: CountryCreate,
        connection: Optional[asyncpg.Connection] = None
    ) -> asyncpg.Record:
        query = """
            INSERT INTO countries (name, code, is_active, is_deleted, created_at, updated_at)
            VALUES ($1, $2, $3, FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id, name, TRIM(code) AS code, is_active, is_deleted, created_at, updated_at
        """
        record = await self.fetch_one(
            query,
            country_in.name,
            country_in.code,
            country_in.is_active,
            connection=connection
        )
        assert record is not None
        return record

    async def update(
        self,
        country_id: UUID,
        country_in: CountryUpdate,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        updates = []
        params = []
        idx = 1

        if country_in.name is not None:
            updates.append(f"name = ${idx}")
            params.append(country_in.name)
            idx += 1

        if country_in.code is not None:
            updates.append(f"code = ${idx}")
            params.append(country_in.code)
            idx += 1

        if country_in.is_active is not None:
            updates.append(f"is_active = ${idx}")
            params.append(country_in.is_active)
            idx += 1

        if not updates:
            return await self.get_by_id(country_id, include_deleted=True, connection=connection)

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(country_id)

        query = f"""
            UPDATE countries
            SET {", ".join(updates)}
            WHERE id = ${idx} AND is_deleted = FALSE
            RETURNING id, name, TRIM(code) AS code, is_active, is_deleted, created_at, updated_at
        """
        return await self.fetch_one(query, *params, connection=connection)

    async def delete(
        self,
        country_id: UUID,
        soft: bool = True,
        connection: Optional[asyncpg.Connection] = None
    ) -> bool:
        if soft:
            query = """
                UPDATE countries
                SET is_deleted = TRUE, is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1 AND is_deleted = FALSE
                RETURNING id
            """
        else:
            query = "DELETE FROM countries WHERE id = $1 RETURNING id"

        res = await self.fetch_one(query, country_id, connection=connection)
        return res is not None


country_repository = CountryRepository()
