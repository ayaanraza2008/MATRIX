"""MATRIX Context Manager.
Maintains sliding-window short-term conversational context, token budgets,
pinned session variables, cross-turn entity resolution, and multi-lingual persona instructions.
"""
from typing import List, Dict, Any, Optional
import re
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
    language: str = "en"  # "en", "hi", "hinglish"


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
        # Extract and update pinned entities from message
        entities = self._extract_entities_from_text(content)
        for k, v in entities.items():
            ctx.pinned_entities[k] = v

        # Detect language preference
        if any(w in content.lower() for w in ["kya", "kaise", "batao", "karo", "namaste", "shukriya", "chahiye"]):
            ctx.language = "hinglish"
        elif any('\u0900' <= char <= '\u097f' for char in content):
            ctx.language = "hi"

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

    def resolve_references(self, session_id: str, prompt: str) -> str:
        """Resolve pronouns and anaphoric references (e.g. 'it', 'that file', 'that app', 'the same')
        using recent context and pinned entities.
        """
        ctx = self.get_context(session_id)
        resolved = prompt

        # Reference to last mentioned file
        last_file = ctx.pinned_entities.get("last_file")
        if last_file:
            resolved = re.sub(r'\b(that file|this file|the file|it)\b', f"'{last_file}'", resolved, flags=re.IGNORECASE)

        # Reference to last mentioned app
        last_app = ctx.pinned_entities.get("last_app")
        if last_app:
            resolved = re.sub(r'\b(that app|this app|the app|the application)\b', f"{last_app}", resolved, flags=re.IGNORECASE)

        # Reference to last search query / URL
        last_query = ctx.pinned_entities.get("last_search_query")
        if last_query:
            resolved = re.sub(r'\b(that topic|the same topic|that research)\b', f"'{last_query}'", resolved, flags=re.IGNORECASE)

        return resolved

    def detect_ambiguity(self, prompt: str, session_id: str) -> Optional[str]:
        """Detect ambiguous or underspecified commands and return targeted clarification questions.
        Returns None if prompt is actionable.
        """
        p_clean = prompt.strip().lower()
        ctx = self.get_context(session_id)

        # Pure pronouns without context
        if p_clean in ["do it", "fix it", "run it", "execute it", "delete it", "open it"]:
            if not ctx.pinned_entities:
                return "Could you please specify which file, application, or task you would like me to work on?"

        # Ambiguous open/close
        if re.match(r'^(open|launch|start|close|kill)\s*$', p_clean):
            return "Which application or file would you like me to open?"

        # Ambiguous search
        if re.match(r'^(search|look up|research|find)\s*$', p_clean):
            return "What topic or website would you like me to research?"

        return None

    def _extract_entities_from_text(self, text: str) -> Dict[str, Any]:
        """Extract files, URLs, apps, or topics mentioned in conversation."""
        entities = {}
        # Windows / Unix File paths
        file_match = re.search(r'([A-Za-z]:\\[^ \t\n\r"\'<>|]+(?:\.[a-zA-Z0-9]+)?|(?:\b[\w-]+\.(?:txt|py|json|md|pdf|csv|docx|png|jpg|exe)\b))', text)
        if file_match:
            entities["last_file"] = file_match.group(1)

        # URLs
        url_match = re.search(r'(https?://[^\s]+)', text)
        if url_match:
            entities["last_url"] = url_match.group(1)

        # Common Apps
        app_match = re.search(r'\b(calc|calculator|notepad|chrome|terminal|cmd|powershell|code|browser)\b', text, re.IGNORECASE)
        if app_match:
            entities["last_app"] = app_match.group(1).lower()

        return entities

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
