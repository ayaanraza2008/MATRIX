"""MATRIX Repository Intelligence: Capability Registry.
Registers, updates, and tracks all accepted repository capabilities in SQLite.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from database.session import AsyncSessionLocal
from database.models import Capability as CapabilityModel
from sqlalchemy import select
from config.logging_config import get_logger

logger = get_logger("repo_intel.registry")


class RegisteredCapability(BaseModel):
    capability_id: str
    name: str
    description: str
    source_repo: Optional[str]
    integration_method: str  # 'native', 'service', 'adapter', 'skill'
    required_permissions: List[str] = []
    is_enabled: bool = True
    is_verified: bool = False


class CapabilityRegistry:
    """Manages verified repository integrations and tool registration."""

    async def register(self, cap: RegisteredCapability) -> bool:
        """Register or update an integration capability in the database."""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(CapabilityModel).where(CapabilityModel.capability_id == cap.capability_id)
                res = await session.execute(stmt)
                existing = res.scalar_one_or_none()

                if existing:
                    existing.name = cap.name
                    existing.description = cap.description
                    existing.source_repo = cap.source_repo
                    existing.integration_method = cap.integration_method
                    existing.is_enabled = cap.is_enabled
                    existing.is_verified = cap.is_verified
                else:
                    new_cap = CapabilityModel(
                        capability_id=cap.capability_id,
                        name=cap.name,
                        description=cap.description,
                        source_repo=cap.source_repo,
                        integration_method=cap.integration_method,
                        required_permissions=cap.required_permissions,
                        is_enabled=cap.is_enabled,
                        is_verified=cap.is_verified
                    )
                    session.add(new_cap)

                await session.commit()
                logger.info(f"Registered capability '{cap.name}' ({cap.capability_id})")
                return True
        except Exception as e:
            logger.error(f"Failed to register capability: {e}")
            return False

    async def list_all(self) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            stmt = select(CapabilityModel)
            res = await session.execute(stmt)
            caps = res.scalars().all()
            return [
                {
                    "capability_id": c.capability_id,
                    "name": c.name,
                    "description": c.description,
                    "source_repo": c.source_repo,
                    "integration_method": c.integration_method,
                    "is_enabled": c.is_enabled,
                    "is_verified": c.is_verified
                }
                for c in caps
            ]


# Global capability registry singleton
capability_registry = CapabilityRegistry()
