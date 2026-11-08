"""MATRIX Memory Management API Route.
Allows users to inspect, create, edit, search, and delete stored personal facts, project contexts,
preferences, routines, and contacts with automatic secret scrubbing.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from memory.manager import memory_manager
from config.logging_config import get_logger

logger = get_logger("api.memory")
router = APIRouter(prefix="/memory", tags=["Personal Knowledge & Memory"])


class MemoryCreatePayload(BaseModel):
    key: str
    content: str
    category: str = "personal"
    tags: List[str] = Field(default_factory=list)
    relevance_score: float = 1.0


class MemorySearchResponse(BaseModel):
    query: str
    total_found: int
    results: List[Dict[str, Any]]


@router.get("", response_model=List[Dict[str, Any]])
async def list_memories(
    category: Optional[str] = Query(None, description="Filter by category: personal, project, preference, routine, contact"),
    limit: int = Query(100, ge=1, le=500)
):
    """Retrieve all stored user memories, preferences, and project context."""
    return await memory_manager.list_memories(category=category, limit=limit)


@router.get("/search", response_model=MemorySearchResponse)
async def search_memories(
    q: str = Query(..., min_length=1, description="Keywords to search"),
    category: Optional[str] = Query(None, description="Optional category filter"),
    limit: int = Query(10, ge=1, le=50)
):
    """Search stored memories by semantic keywords with relevance ranking."""
    results = await memory_manager.search_memory(query=q, category=category, limit=limit)
    return {
        "query": q,
        "total_found": len(results),
        "results": results
    }


@router.get("/categories")
async def get_categories():
    """Return available memory categories."""
    return {
        "categories": list(memory_manager.CATEGORIES),
        "descriptions": {
            "personal": "User profile, background, identity, and personal context",
            "project": "Workspaces, active repositories, milestones, architectural decisions",
            "preference": "Editor choices, themes, notification thresholds, coding styles",
            "routine": "Schedules, daily briefings, recurring habits, quiet hours",
            "contact": "Frequent collaborators, emergency numbers, VIP contacts"
        }
    }


@router.get("/export")
async def export_all_memories():
    """Export all memory entries for backup or offline storage."""
    memories = await memory_manager.export_memories()
    return {
        "count": len(memories),
        "memories": memories
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def store_memory(payload: MemoryCreatePayload):
    """Save an approved user memory or preference with privacy scrubbing."""
    saved = await memory_manager.add_memory(
        key=payload.key,
        content=payload.content,
        category=payload.category,
        tags=payload.tags,
        relevance_score=payload.relevance_score
    )
    return saved


@router.delete("/{key_or_id}", status_code=status.HTTP_200_OK)
async def delete_memory(key_or_id: str):
    """Delete a stored memory record by key or ID."""
    deleted = await memory_manager.delete_memory(key_or_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Memory entry '{key_or_id}' not found.")
    logger.info(f"Deleted user memory: '{key_or_id}'")
    return {"status": "DELETED", "key_or_id": key_or_id}
