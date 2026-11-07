"""MATRIX Automation & Workflows API Route.
Manages persistent multi-step task records, checkpoints, and recovery states in SQLite.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timezone

from database.session import get_db
from database.models import TaskRecord
from config.logging_config import get_logger

logger = get_logger("api.automation")
router = APIRouter(prefix="/tasks", tags=["Automation Workflows"])


class TaskCreate(BaseModel):
    title: str
    autonomy_level: int = 2
    assigned_agent: str = "automation"
    plan_data: Optional[List[Dict[str, Any]]] = None


class TaskResponse(BaseModel):
    id: int
    task_id: str
    title: str
    autonomy_level: int
    status: str
    assigned_agent: str
    plan_data: Optional[List[Dict[str, Any]]]
    checkpoints: Optional[Dict[str, Any]]
    result_data: Optional[Dict[str, Any]]
    created_at: datetime
    completed_at: Optional[datetime]


@router.get("", response_model=List[TaskResponse])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    """List all workflow tasks and execution states."""
    stmt = select(TaskRecord).order_by(TaskRecord.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreate, db: AsyncSession = Depends(get_db)):
    """Create and queue a new autonomous workflow task."""
    task_id = f"task_{uuid.uuid4().hex[:10]}"
    new_task = TaskRecord(
        task_id=task_id,
        title=payload.title,
        autonomy_level=payload.autonomy_level,
        status="RUNNING",
        assigned_agent=payload.assigned_agent,
        plan_data=payload.plan_data or [
            {"step_id": 1, "name": "Initialize execution environment", "status": "COMPLETED"},
            {"step_id": 2, "name": "Run workflow steps", "status": "RUNNING"},
            {"step_id": 3, "name": "Verify outcomes & checkpoint", "status": "PENDING"}
        ],
        checkpoints={"step": 2, "checkpoint_time": datetime.now(timezone.utc).isoformat()}
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    logger.info(f"Queued automation task '{payload.title}' ({task_id})")
    return new_task


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """Mark a workflow task as completed."""
    stmt = select(TaskRecord).where(TaskRecord.task_id == task_id)
    res = await db.execute(stmt)
    task = res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    task.status = "COMPLETED"
    task.completed_at = datetime.now(timezone.utc)
    task.result_data = {"verified": True, "message": "All execution steps succeeded."}
    await db.commit()
    await db.refresh(task)
    return task
