"""MATRIX Context Manager.
Maintains sliding-window short-term conversational context, token budgets,
pinned session variables, and multi-lingual persona instructions.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from config.settings import settings


class ContextMessage(BaseModel):
    role: str  # 'system', 'user', 'assistant', 'agent'
    content: str
    agent_name: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationContext(BaseModel):
    session_id: str
    messages: List[ContextMessage] = Field(default_factory=list)
    pinned_entities: Dict[str, Any] = Field(default_factory=dict)
    active_agent: str = "core"
    max_tokens: int = 8192
    estimated_tokens: int = 0


class ContextManager:
    """Manages active conversational context across agents and sessions."""

    SYSTEM_PROMPT = (
        "You are MATRIX, an intelligent, calm, professional, and conversational personal AI assistant "
        "inspired by JARVIS from Iron Man. You act as an intelligent digital operating layer between "
        "the user and their PC (Windows 11, AMD Ryzen 7 5700U) and Android companion.\n"
        "Capabilities & Rules:\n"
        "1. Speak English, Hindi, and Hinglish naturally depending on user preference.\n"
        "2. Keep responses concise, direct, and actionable. Never use excessive narration.\n"
        "3. Local-first: Storage and data are in D:\\matrix_data.\n"
        "4. Always verify completed actions and never simulate fake success.\n"
        "5. Adhere strictly to the deterministic policy layer: never execute destructive actions without confirmation."
    )

    def __init__(self):
        self._contexts: Dict[str, ConversationContext] = {}

    def get_context(self, session_id: str) -> ConversationContext:
        if session_id not in self._contexts:
            ctx = ConversationContext(session_id=session_id)
            # Seed system prompt
            ctx.messages.append(ContextMessage(
                role="system",
                content=self.SYSTEM_PROMPT
            ))
            self._contexts[session_id] = ctx
        return self._contexts[session_id]

    def add_message(self, session_id: str, role: str, content: str, agent_name: Optional[str] = None):
        ctx = self.get_context(session_id)
        ctx.messages.append(ContextMessage(
            role=role,
            content=content,
            agent_name=agent_name
        ))
        # Estimate tokens (~4 chars per token)
        ctx.estimated_tokens = sum(len(m.content) // 4 for m in ctx.messages)

        # Sliding window pruning if exceeding budget
        while ctx.estimated_tokens > ctx.max_tokens and len(ctx.messages) > 3:
            # Preserve system prompt at index 0
            removed = ctx.messages.pop(1)
            ctx.estimated_tokens -= len(removed.content) // 4

    def pin_entity(self, session_id: str, key: str, value: Any):
        ctx = self.get_context(session_id)
        ctx.pinned_entities[key] = value

    def format_history_for_llm(self, session_id: str) -> str:
        ctx = self.get_context(session_id)
        formatted = []
        for m in ctx.messages:
            prefix = f"{m.role.upper()}"
            if m.agent_name:
                prefix += f" ({m.agent_name})"
            formatted.append(f"{prefix}: {m.content}")
        return "\n\n".join(formatted)


# Global Context Manager singleton
context_manager = ContextManager()
