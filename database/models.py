"""MATRIX Database Models.
SQLAlchemy Async ORM models for devices, sessions, messages, tasks, audit trails, and preferences.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, JSON
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


class Device(Base):
    """Registered devices (PC, Android, Local Clients) with authorization status."""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    platform = Column(String(30), nullable=False)  # 'windows', 'linux', 'android', 'web'
    is_paired = Column(Boolean, default=False, nullable=False)
    auth_token_hash = Column(String(128), nullable=True)
    public_key = Column(Text, nullable=True)
    last_ip = Column(String(45), nullable=True)
    last_seen_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class UserPreference(Base):
    """User-approved preferences, identity, and personal settings."""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=False)
    category = Column(String(50), default="general", nullable=False)
    is_user_editable = Column(Boolean, default=True, nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )


class Session(Base):
    """Conversational sessions between user and MATRIX."""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(String(200), default="New Session", nullable=False)
    active_agent = Column(String(50), default="core", nullable=False)
    model_used = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    """Individual chat & voice messages."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system', 'agent'
    content = Column(Text, nullable=False)
    agent_name = Column(String(50), nullable=True)
    tokens_used = Column(Integer, default=0)
    extra_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    session = relationship("Session", back_populates="messages")


class TaskRecord(Base):
    """Autonomous and multi-step tasks execution history."""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    autonomy_level = Column(Integer, default=1, nullable=False)  # 0 to 4
    status = Column(String(30), default="PENDING", nullable=False)  # PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
    assigned_agent = Column(String(50), default="orchestrator", nullable=False)
    plan_data = Column(JSON, nullable=True)
    checkpoints = Column(JSON, nullable=True)
    result_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime, nullable=True)


class AuditLog(Base):
    """Immutable security audit trail for all system commands and agent actions."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(50), nullable=False, index=True)
    risk_level = Column(Integer, nullable=False)  # 0 to 4
    tool_name = Column(String(100), nullable=True)
    actor = Column(String(50), nullable=False)  # 'user', 'agent:computer', 'system', etc.
    action_summary = Column(Text, nullable=False)
    payload = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False)  # 'ALLOWED', 'BLOCKED', 'APPROVED', 'REJECTED'
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)


class Capability(Base):
    """Installed skills, adapters, and tools registry."""
    __tablename__ = "capabilities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    capability_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    source_repo = Column(String(200), nullable=True)
    integration_method = Column(String(30), nullable=False)  # 'native', 'service', 'adapter', 'skill'
    required_permissions = Column(JSON, default=list)
    is_enabled = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
