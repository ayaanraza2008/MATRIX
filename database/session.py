"""MATRIX Async Database Session Manager.
Manages SQLite async engine with aiosqlite, connection pooling, and lifecycle.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy import text
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("database")

# Initialize SQLite Async Engine
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False}
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection yield for FastAPI request handlers."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session rollback triggered by error: {e}")
            raise
        finally:
            await session.close()


async def check_db_health() -> bool:
    """Check whether the SQLite database connection is operational."""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
