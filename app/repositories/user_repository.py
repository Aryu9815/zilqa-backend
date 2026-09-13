from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID
import asyncpg

from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository):
    
    async def get_by_id(
        self,
        user_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        query = """
            SELECT id, name, email, mobile_number, password_hash, google_id, role, is_active, created_at, updated_at
            FROM users
            WHERE id = $1
        """
        return await self.fetch_one(query, user_id, connection=connection)

    async def get_by_email(
        self,
        email: str,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        query = """
            SELECT id, name, email, mobile_number, password_hash, google_id, role, is_active, created_at, updated_at
            FROM users
            WHERE LOWER(email) = LOWER($1)
            LIMIT 1
        """
        return await self.fetch_one(query, email, connection=connection)

    async def get_by_google_id(
        self,
        google_id: str,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        query = """
            SELECT id, name, email, mobile_number, password_hash, google_id, role, is_active, created_at, updated_at
            FROM users
            WHERE google_id = $1
            LIMIT 1
        """
        return await self.fetch_one(query, google_id, connection=connection)

    async def create(
        self,
        name: str,
        email: str,
        password_hash: Optional[str] = None,
        role: str = "customer",
        google_id: Optional[str] = None,
        mobile_number: Optional[str] = None,
        connection: Optional[asyncpg.Connection] = None
    ) -> asyncpg.Record:
        query = """
            INSERT INTO users (name, email, password_hash, google_id, mobile_number, role, is_active, created_at, updated_at)
            VALUES ($1, LOWER($2), $3, $4, $5, $6, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id, name, email, mobile_number, google_id, role, is_active, created_at, updated_at
        """
        record = await self.fetch_one(query, name, email, password_hash, google_id, mobile_number, role, connection=connection)
        assert record is not None
        return record

    async def link_google_id(
        self,
        user_id: UUID,
        google_id: str,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        query = """
            UPDATE users
            SET google_id = $1, updated_at = CURRENT_TIMESTAMP
            WHERE id = $2
            RETURNING id, name, email, mobile_number, google_id, role, is_active, created_at, updated_at
        """
        return await self.fetch_one(query, google_id, user_id, connection=connection)

    async def update(
        self,
        user_id: UUID,
        name: Optional[str] = None,
        email: Optional[str] = None,
        password_hash: Optional[str] = None,
        is_active: Optional[bool] = None,
        google_id: Optional[str] = None,
        mobile_number: Optional[str] = None,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        updates = []
        params = []
        idx = 1

        if name is not None:
            updates.append(f"name = ${idx}")
            params.append(name)
            idx += 1
        if email is not None:
            updates.append(f"email = LOWER(${idx})")
            params.append(email)
            idx += 1
        if password_hash is not None:
            updates.append(f"password_hash = ${idx}")
            params.append(password_hash)
            idx += 1
        if is_active is not None:
            updates.append(f"is_active = ${idx}")
            params.append(is_active)
            idx += 1
        if google_id is not None:
            updates.append(f"google_id = ${idx}")
            params.append(google_id)
            idx += 1
        if mobile_number is not None:
            updates.append(f"mobile_number = ${idx}")
            params.append(mobile_number)
            idx += 1

        if not updates:
            return await self.get_by_id(user_id, connection=connection)

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(user_id)
        
        query = f"""
            UPDATE users
            SET {", ".join(updates)}
            WHERE id = ${idx}
            RETURNING id, name, email, mobile_number, google_id, role, is_active, created_at, updated_at
        """
        return await self.fetch_one(query, *params, connection=connection)

    # ----------------- Refresh Tokens -----------------

    async def save_refresh_token(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        connection: Optional[asyncpg.Connection] = None
    ) -> asyncpg.Record:
        query = """
            INSERT INTO refresh_tokens (user_id, token_hash, expires_at, revoked, created_at)
            VALUES ($1, $2, $3, FALSE, CURRENT_TIMESTAMP)
            RETURNING id, user_id, token_hash, expires_at, revoked, created_at
        """
        record = await self.fetch_one(query, user_id, token_hash, expires_at, connection=connection)
        assert record is not None
        return record

    async def get_refresh_token(
        self,
        token_hash: str,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        query = """
            SELECT id, user_id, token_hash, expires_at, revoked, created_at
            FROM refresh_tokens
            WHERE token_hash = $1
        """
        return await self.fetch_one(query, token_hash, connection=connection)

    async def revoke_refresh_token(
        self,
        token_hash: str,
        connection: Optional[asyncpg.Connection] = None
    ) -> bool:
        query = """
            UPDATE refresh_tokens
            SET revoked = TRUE
            WHERE token_hash = $1 AND revoked = FALSE
            RETURNING id
        """
        res = await self.fetch_one(query, token_hash, connection=connection)
        return res is not None

    async def revoke_all_user_tokens(
        self,
        user_id: UUID,
        connection: Optional[asyncpg.Connection] = None
    ) -> None:
        query = """
            UPDATE refresh_tokens
            SET revoked = TRUE
            WHERE user_id = $1 AND revoked = FALSE
        """
        await self.execute(query, user_id, connection=connection)


user_repository = UserRepository()
