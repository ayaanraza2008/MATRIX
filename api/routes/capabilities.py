"""MATRIX Capabilities & Skills Registry Route.
Surfaces verified capabilities, specialized agents, and repository integrations.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pydantic import BaseModel
from database.session import get_db
from database.models import Capability as CapabilityModel

router = APIRouter(prefix="/capabilities", tags=["Capabilities & Agents"])


class CapabilityResponse(BaseModel):
    id: int
    capability_id: str
    name: str
    description: str
    source_repo: str | None
    integration_method: str
    is_enabled: bool
    is_verified: bool


# Default core capabilities present in MATRIX
CORE_CAPABILITIES = [
    {
        "capability_id": "core_orchestrator",
        "name": "Central Orchestrator",
        "description": "Multi-agent coordination, intent decomposition, and plan execution",
        "source_repo": "NousResearch/hermes-agent",
        "integration_method": "native",
        "is_enabled": True,
        "is_verified": True
    },
    {
        "capability_id": "computer_control",
        "name": "PC Computer Agent",
        "description": "Deterministic mouse, keyboard, window, and application automation",
        "source_repo": "internal/pywinauto",
        "integration_method": "native",
        "is_enabled": True,
        "is_verified": False
    },
    {
        "capability_id": "browser_intelligence",
        "name": "Browser Agent",
        "description": "Headless and visual browser automation, web research, page analysis",
        "source_repo": "browser-use/browser-use",
        "integration_method": "adapter",
        "is_enabled": True,
        "is_verified": False
    },
    {
        "capability_id": "voice_interaction",
        "name": "JARVIS Voice System",
        "description": "Wake-word detection, offline STT (Whisper), and natural TTS (Piper/Kokoro)",
        "source_repo": "resemble-ai/chatterbox",
        "integration_method": "native",
        "is_enabled": True,
        "is_verified": False
    },
    {
        "capability_id": "android_sync",
        "name": "Android Mobile Companion",
        "description": "Remote task routing, mobile notifications, and device bridge",
        "source_repo": "mobile-next/mobile-mcp",
        "integration_method": "service",
        "is_enabled": True,
        "is_verified": False
    },
    {
        "capability_id": "security_audit",
        "name": "Security & Permission Gate",
        "description": "Deterministic policy enforcement, sandboxed execution, and MITRE mapping",
        "source_repo": "0x4m4/hexstrike-ai",
        "integration_method": "adapter",
        "is_enabled": True,
        "is_verified": True
    }
]


@router.get("", response_model=List[CapabilityResponse])
async def list_capabilities(db: AsyncSession = Depends(get_db)):
    """Retrieve all installed and registered capabilities in MATRIX."""
    stmt = select(CapabilityModel)
    result = await db.execute(stmt)
    caps = result.scalars().all()

    if not caps:
        # Seed core capabilities into DB if empty
        for item in CORE_CAPABILITIES:
            cap_record = CapabilityModel(
                capability_id=item["capability_id"],
                name=item["name"],
                description=item["description"],
                source_repo=item["source_repo"],
                integration_method=item["integration_method"],
                is_enabled=item["is_enabled"],
                is_verified=item["is_verified"]
            )
            db.add(cap_record)
        await db.commit()

        # Re-fetch
        stmt = select(CapabilityModel)
        result = await db.execute(stmt)
        caps = result.scalars().all()

    return caps
