from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

# Adjust the database URL to use asyncpg driver if it doesn't already
sqlalchemy_url = settings.DATABASE_URL
if sqlalchemy_url.startswith("postgresql://"):
    sqlalchemy_url = sqlalchemy_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    sqlalchemy_url,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_MAX_SIZE,
    max_overflow=10,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db():
    """Dependency to provide a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
