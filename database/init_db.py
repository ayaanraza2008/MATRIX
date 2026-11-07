"""MATRIX Database Initialization and Schema Migration.
Creates required SQLite tables and registers initial default configurations.
"""
import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from database.session import engine, AsyncSessionLocal
from database.models import Base, UserPreference
from config.logging_config import get_logger

logger = get_logger("database.init")


async def init_database() -> bool:
    """Create all database tables if they do not exist and seed defaults."""
    logger.info("Initializing MATRIX SQLite database tables...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema initialized successfully.")

        # Seed initial system configuration if empty
        async with AsyncSessionLocal() as session:
            stmt = select(UserPreference).where(UserPreference.key == "system_identity")
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if not existing:
                default_pref = UserPreference(
                    key="system_identity",
                    value={
                        "assistant_name": "MATRIX",
                        "personality": "Intelligent, calm, professional, and conversational",
                        "languages": ["English", "Hindi", "Hinglish"],
                        "autonomy_level": 3,
                        "created_at": datetime.now(timezone.utc).isoformat()
                    },
                    category="identity",
                    is_user_editable=True
                )
                session.add(default_pref)
                await session.commit()
                logger.info("Default system identity preference seeded.")

        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(init_database())
