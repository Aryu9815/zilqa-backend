from typing import Any, List, Optional, Sequence
import asyncpg

from app.core.database import execute, executemany, fetch_all, fetch_one, fetch_val


class BaseRepository:
    """Base repository class providing direct asyncpg query helpers."""

    @staticmethod
    async def fetch_one(
        query: str,
        *args: Any,
        connection: Optional[asyncpg.Connection] = None
    ) -> Optional[asyncpg.Record]:
        return await fetch_one(query, *args, connection=connection)

    @staticmethod
    async def fetch_all(
        query: str,
        *args: Any,
        connection: Optional[asyncpg.Connection] = None
    ) -> List[asyncpg.Record]:
        return await fetch_all(query, *args, connection=connection)

    @staticmethod
    async def fetch_val(
        query: str,
        *args: Any,
        column: int = 0,
        connection: Optional[asyncpg.Connection] = None
    ) -> Any:
        return await fetch_val(query, *args, column=column, connection=connection)

    @staticmethod
    async def execute(
        query: str,
        *args: Any,
        connection: Optional[asyncpg.Connection] = None
    ) -> str:
        return await execute(query, *args, connection=connection)

    @staticmethod
    async def executemany(
        query: str,
        args: Sequence[Sequence[Any]],
        connection: Optional[asyncpg.Connection] = None
    ) -> None:
        await executemany(query, args, connection=connection)
