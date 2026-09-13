from typing import List, Optional
from uuid import UUID
import asyncpg

from app.core.database import get_transaction
from app.repositories.base_repository import BaseRepository
from app.schemas.address import AddressCreate, AddressUpdate


class AddressRepository(BaseRepository):

    async def get_by_id_and_user(
        self,
        address_id: UUID,
        user_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        query = """
            SELECT id, user_id, full_name, phone, address_line_1, address_line_2,
                   city, state, postal_code, country, is_default, created_at, updated_at
            FROM user_addresses
            WHERE id = $1 AND user_id = $2
        """
        return await self.fetch_one(query, address_id, user_id, connection=connection)

    async def list_by_user(
        self,
        user_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> List[asyncpg.Record]:
        query = """
            SELECT id, user_id, full_name, phone, address_line_1, address_line_2,
                   city, state, postal_code, country, is_default, created_at, updated_at
            FROM user_addresses
            WHERE user_id = $1
            ORDER BY is_default DESC, created_at DESC
        """
        return await self.fetch_all(query, user_id, connection=connection)

    async def count_by_user(
        self,
        user_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> int:
        query = "SELECT COUNT(*) FROM user_addresses WHERE user_id = $1"
        return await self.fetch_val(query, user_id, connection=connection) or 0

    async def create(
        self,
        user_id: UUID,
        address_in: AddressCreate,
        connection: Optional[asyncpg.Connection] = None
    ) -> asyncpg.Record:
        # If marked default or this is user's first address, unset others
        if address_in.is_default:
            await self.unset_all_defaults(user_id, connection=connection)

        query = """
            INSERT INTO user_addresses (
                user_id, full_name, phone, address_line_1, address_line_2,
                city, state, postal_code, country, is_default, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id, user_id, full_name, phone, address_line_1, address_line_2,
                      city, state, postal_code, country, is_default, created_at, updated_at
        """
        record = await self.fetch_one(
            query,
            user_id,
            address_in.full_name,
            address_in.phone,
            address_line_1 := address_in.address_line_1,
            address_in.address_line_2,
            address_in.city,
            address_in.state,
            address_in.postal_code,
            address_in.country,
            address_in.is_default,
            connection=connection
        )
        assert record is not None
        return record

    async def update(
        self,
        address_id: UUID,
        user_id: UUID,
        address_in: AddressUpdate,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        if address_in.is_default is True:
            await self.unset_all_defaults(user_id, connection=connection)

        updates = []
        params = []
        idx = 1

        fields = [
            ("full_name", address_in.full_name),
            ("phone", address_in.phone),
            ("address_line_1", address_in.address_line_1),
            ("address_line_2", address_in.address_line_2),
            ("city", address_in.city),
            ("state", address_in.state),
            ("postal_code", address_in.postal_code),
            ("country", address_in.country),
            ("is_default", address_in.is_default),
        ]

        for col, val in fields:
            if val is not None:
                updates.append(f"{col} = ${idx}")
                params.append(val)
                idx += 1

        if not updates:
            return await self.get_by_id_and_user(address_id, user_id, connection=connection)

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.extend([address_id, user_id])
        
        query = f"""
            UPDATE user_addresses
            SET {", ".join(updates)}
            WHERE id = ${idx} AND user_id = ${idx + 1}
            RETURNING id, user_id, full_name, phone, address_line_1, address_line_2,
                      city, state, postal_code, country, is_default, created_at, updated_at
        """
        return await self.fetch_one(query, *params, connection=connection)

    async def delete(
        self,
        address_id: UUID,
        user_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> bool:
        query = "DELETE FROM user_addresses WHERE id = $1 AND user_id = $2 RETURNING id"
        res = await self.fetch_one(query, address_id, user_id, connection=connection)
        return res is not None

    async def set_default(
        self,
        address_id: UUID,
        user_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        async def _execute(conn: asyncpg.Connection):
            await self.unset_all_defaults(user_id, connection=conn)
            query = """
                UPDATE user_addresses
                SET is_default = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1 AND user_id = $2
                RETURNING id, user_id, full_name, phone, address_line_1, address_line_2,
                          city, state, postal_code, country, is_default, created_at, updated_at
            """
            return await self.fetch_one(query, address_id, user_id, connection=conn)

        if connection is not None:
            return await _execute(connection)
        async with get_transaction() as conn:
            return await _execute(conn)

    async def unset_all_defaults(
        self,
        user_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> None:
        query = """
            UPDATE user_addresses
            SET is_default = FALSE, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = $1 AND is_default = TRUE
        """
        await self.execute(query, user_id, connection=connection)


address_repository = AddressRepository()
