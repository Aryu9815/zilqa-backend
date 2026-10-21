import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, List, Optional, Sequence
import asyncpg

from app.core.config import settings

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def init_db_pool() -> asyncpg.Pool:
    """Initialize the global asyncpg connection pool."""
    global _pool
    if _pool is None:
        logger.info("Initializing asyncpg connection pool...")
        _pool = await asyncpg.create_pool(
            dsn=settings.DATABASE_URL,
            min_size=settings.DB_POOL_MIN_SIZE,
            max_size=settings.DB_POOL_MAX_SIZE,
            max_inactive_connection_lifetime=settings.DB_POOL_MAX_INACTIVE_CONNECTION_LIFETIME,
            timeout=settings.DB_POOL_TIMEOUT,
            ssl="require",
        )
        logger.info("asyncpg connection pool initialized successfully.")
        try:
            async with _pool.acquire() as conn:
                await conn.execute("""
                    ALTER TABLE cart_items DROP CONSTRAINT IF EXISTS uq_cart_items_cart_product;
                    DROP INDEX IF EXISTS uq_cart_items_cart_product;
                    DROP INDEX IF EXISTS uq_cart_items_cart_product_size;
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_cart_items_cart_product_size 
                    ON cart_items (cart_id, product_id, LOWER(COALESCE(TRIM(size), '')));

                    ALTER TABLE products ADD COLUMN IF NOT EXISTS variants JSONB NOT NULL DEFAULT '[]'::jsonb;
                    ALTER TABLE products ADD COLUMN IF NOT EXISTS variant_name VARCHAR(255) NOT NULL DEFAULT '';
                """)
        except Exception as e:
            logger.warning("Could not execute schema migrations in init_db_pool: %s", e)
    return _pool


async def close_db_pool() -> None:
    """Close the global asyncpg connection pool."""
    global _pool
    if _pool is not None:
        logger.info("Closing asyncpg connection pool...")
        await _pool.close()
        _pool = None
        logger.info("asyncpg connection pool closed.")


def get_pool() -> asyncpg.Pool:
    """Get the current initialized asyncpg connection pool."""
    if _pool is None:
        raise RuntimeError("Database connection pool is not initialized. Ensure app lifespan is active.")
    return _pool


@asynccontextmanager
async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Acquire a connection from the pool."""
    pool = get_pool()
    async with pool.acquire() as connection:
        yield connection


@asynccontextmanager
async def get_transaction() -> AsyncGenerator[asyncpg.Connection, None]:
    """Acquire a connection and manage a database transaction."""
    pool = get_pool()
    async with pool.acquire() as connection:
        async with connection.transaction():
            yield connection


async def fetch_one(
    query: str,
    *args: Any,
    connection: Optional[asyncpg.Connection] = None
) -> Optional[asyncpg.Record]:
    """Execute a query and fetch a single record."""
    if connection is not None:
        return await connection.fetchrow(query, *args)
    async with get_connection() as conn:
        return await conn.fetchrow(query, *args)


async def fetch_all(
    query: str,
    *args: Any,
    connection: Optional[asyncpg.Connection] = None
) -> List[asyncpg.Record]:
    """Execute a query and fetch all matching records."""
    if connection is not None:
        return await connection.fetch(query, *args)
    async with get_connection() as conn:
        return await conn.fetch(query, *args)


async def fetch_val(
    query: str,
    *args: Any,
    column: int = 0,
    connection: Optional[asyncpg.Connection] = None
) -> Any:
    """Execute a query and fetch a single value."""
    if connection is not None:
        return await connection.fetchval(query, *args, column=column)
    async with get_connection() as conn:
        return await conn.fetchval(query, *args, column=column)


async def execute(
    query: str,
    *args: Any,
    connection: Optional[asyncpg.Connection] = None
) -> str:
    """Execute a command (INSERT, UPDATE, DELETE, etc.) and return status."""
    if connection is not None:
        return await connection.execute(query, *args)
    async with get_connection() as conn:
        return await conn.execute(query, *args)


async def executemany(
    query: str,
    args: Sequence[Sequence[Any]],
    connection: Optional[asyncpg.Connection] = None
) -> None:
    """Execute a command against multiple parameter sets."""
    if connection is not None:
        await connection.executemany(query, args)
        return
    async with get_connection() as conn:
        await conn.executemany(query, args)
