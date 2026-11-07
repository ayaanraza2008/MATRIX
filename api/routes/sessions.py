"""MATRIX Conversation Sessions & Messages Route.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
import uuid
from datetime import datetime, timezone

from database.session import get_db
from database.models import Session as SessionModel, Message as MessageModel
from config.logging_config import get_logger

logger = get_logger("api.sessions")
router = APIRouter(prefix="/sessions", tags=["Conversations"])


class SessionCreate(BaseModel):
    title: Optional[str] = "New Mission"
    active_agent: Optional[str] = "core"


class MessageCreate(BaseModel):
    role: str = "user"
    content: str
    agent_name: Optional[str] = "core"


class MessageResponse(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    agent_name: Optional[str]
    created_at: datetime


class SessionResponse(BaseModel):
    id: int
    session_id: str
    title: str
    active_agent: str
    created_at: datetime
    updated_at: datetime


@router.get("", response_model=List[SessionResponse])
async def list_sessions(db: AsyncSession = Depends(get_db)):
    """List all conversation sessions ordered by most recently updated."""
    stmt = select(SessionModel).order_by(SessionModel.updated_at.desc())
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    return sessions


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(payload: SessionCreate, db: AsyncSession = Depends(get_db)):
    """Create a new conversational session."""
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    new_session = SessionModel(
        session_id=session_id,
        title=payload.title or "New Mission",
        active_agent=payload.active_agent or "core"
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    logger.info(f"Created session {session_id} ('{new_session.title}')")
    return new_session


@router.get("/{session_id}/messages", response_model=List[MessageResponse])
async def get_session_messages(session_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve messages for a given session."""
    stmt = select(SessionModel).where(SessionModel.session_id == session_id)
    result = await db.execute(stmt)
    sess = result.scalar_one_or_none()
    if not sess:
        sess = SessionModel(
            session_id=session_id,
            title="Auto Session",
            active_agent="core"
        )
        db.add(sess)
        await db.commit()

    msg_stmt = select(MessageModel).where(MessageModel.session_id == session_id).order_by(MessageModel.created_at.asc())
    msg_result = await db.execute(msg_stmt)
    return msg_result.scalars().all()


@router.post("/{session_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def post_message(session_id: str, payload: MessageCreate, db: AsyncSession = Depends(get_db)):
    """Add a message to the session."""
    stmt = select(SessionModel).where(SessionModel.session_id == session_id)
    result = await db.execute(stmt)
    sess = result.scalar_one_or_none()
    if not sess:
        sess = SessionModel(
            session_id=session_id,
            title="Auto Session",
            active_agent="core"
        )
        db.add(sess)
        await db.commit()

    new_msg = MessageModel(
        session_id=session_id,
        role=payload.role,
        content=payload.content,
        agent_name=payload.agent_name
    )
    db.add(new_msg)
    sess.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(new_msg)

    # If this is a user message, trigger MATRIX Brain processing
    if payload.role == "user":
        from core.brain import brain
        import asyncio
        asyncio.create_task(brain.process_user_request(session_id, payload.content, payload.agent_name))

    return new_msg


@router.post("/{session_id}/interact")
async def interact_session(session_id: str, payload: MessageCreate, db: AsyncSession = Depends(get_db)):
    """Synchronous interaction: processes prompt via Brain and returns the assistant's reply."""
    stmt = select(SessionModel).where(SessionModel.session_id == session_id)
    result = await db.execute(stmt)
    sess = result.scalar_one_or_none()
    if not sess:
        sess = SessionModel(
            session_id=session_id,
            title="Auto Session",
            active_agent="core"
        )
        db.add(sess)
        await db.commit()

    # Save user message
    user_msg = MessageModel(
        session_id=session_id,
        role="user",
        content=payload.content,
        agent_name=payload.agent_name
    )
    db.add(user_msg)
    await db.commit()

    # Process through MATRIX Brain
    from core.brain import brain
    brain_res = await brain.process_user_request(session_id, payload.content, payload.agent_name)

    return {
        "session_id": session_id,
        "reply": brain_res["response"],
        "plan_status": brain_res["plan_status"],
        "latency_ms": brain_res["latency_ms"]
    }
