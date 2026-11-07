"""MATRIX Memory Management API Route.
Allows users to inspect, create, edit, and delete stored personal facts with zero fabrication.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from typing import List, Dict, Any
from database.session import get_db
from database.models import UserPreference
from config.logging_config import get_logger

logger = get_logger("api.memory")
router = APIRouter(prefix="/memory", tags=["Personal Knowledge & Memory"])


class MemoryCreate(BaseModel):
    key: str
    value: Dict[str, Any]
    category: str = "user_memory"


class MemoryResponse(BaseModel):
    id: int
    key: str
    value: Dict[str, Any]
    category: str


@router.get("", response_model=List[MemoryResponse])
async def list_memories(db: AsyncSession = Depends(get_db)):
    """Retrieve all stored user preferences and factual memories."""
    stmt = select(UserPreference).order_by(UserPreference.updated_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def store_memory(payload: MemoryCreate, db: AsyncSession = Depends(get_db)):
    """Save an approved user memory or preference."""
    stmt = select(UserPreference).where(UserPreference.key == payload.key)
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()

    if existing:
        existing.value = payload.value
        existing.category = payload.category
        await db.commit()
        await db.refresh(existing)
        return existing
    else:
        new_pref = UserPreference(
            key=payload.key,
            value=payload.value,
            category=payload.category,
            is_user_editable=True
        )
        db.add(new_pref)
        await db.commit()
        await db.refresh(new_pref)
        return new_pref


@router.delete("/{key}", status_code=status.HTTP_200_OK)
async def delete_memory(key: str, db: AsyncSession = Depends(get_db)):
    """Delete a stored memory record."""
    stmt = delete(UserPreference).where(UserPreference.key == key)
    res = await db.execute(stmt)
    await db.commit()
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="Memory entry not found.")
    logger.info(f"Deleted user memory key: '{key}'")
    return {"status": "DELETED", "key": key}
