"""MATRIX Hierarchical Persistent Memory & Context Manager.
Provides categorized context (personal, project, preference, routine, contact),
semantic search, relevance scoring, and an automated secret/credential privacy scrubber.
Persists to the SQLite 'memories' table via AsyncSessionLocal.
"""
from typing import List, Dict, Any, Optional, Tuple
import re
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, or_, and_, delete, update
from database.session import AsyncSessionLocal
from database.models import MemoryEntry
from config.logging_config import get_logger

logger = get_logger("memory.manager")

# Privacy scrubber patterns for sensitive tokens, passwords, and secrets
SECRET_PATTERNS = [
    # Google API Key
    (re.compile(r"AIza[0-9A-Za-z_\-]{30,45}"), "[REDACTED_API_KEY]"),
    # OpenAI API Key
    (re.compile(r"sk-[a-zA-Z0-9_\-]{20,60}"), "[REDACTED_OPENAI_KEY]"),
    # GitHub Token
    (re.compile(r"gh[pousr]_[0-9a-zA-Z]{30,255}"), "[REDACTED_GITHUB_TOKEN]"),
    # Generic Bearer Tokens
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9\-_\.=]{20,}"), "Bearer [REDACTED_TOKEN]"),
    # Passwords in key-value pairs
    (re.compile(r"(?i)(password|passwd|pwd|api_secret)\s*[:=]\s*['\"]?([^\s'\"]{6,})['\"]?"), r"\1=[REDACTED_SECRET]"),
    # Credit Card Numbers
    (re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"), "[REDACTED_PAYMENT_CARD]"),
    # Private Key Headers
    (re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+ PRIVATE KEY-----"), "[REDACTED_PRIVATE_KEY]"),
]


class MemoryManager:
    """Enterprise-grade context and personal memory management system."""

    CATEGORIES = ("personal", "project", "preference", "routine", "contact")

    def __init__(self):
        self._short_term_cache: List[Dict[str, Any]] = []
        self._max_short_term: int = 20

    def scrub_text(self, text: str) -> Tuple[str, bool]:
        """Scrub known API keys, credentials, and payment data from text."""
        sanitized = text
        detected = False
        for pattern, replacement in SECRET_PATTERNS:
            if pattern.search(sanitized):
                detected = True
                sanitized = pattern.sub(replacement, sanitized)
        return sanitized, detected

    async def add_memory(
        self,
        key: str,
        content: str,
        category: str = "personal",
        tags: Optional[List[str]] = None,
        relevance_score: float = 1.0,
        enforce_privacy: bool = True
    ) -> Dict[str, Any]:
        """Add or update a persistent memory entry with privacy protection."""
        if category not in self.CATEGORIES:
            category = "personal"

        sanitized_content, secret_found = self.scrub_text(content)
        if secret_found and enforce_privacy:
            logger.warning(f"Privacy scrubber redacted sensitive credentials in memory key '{key}'.")

        tags = tags or []
        memory_id = f"mem_{uuid.uuid4().hex[:12]}"

        async with AsyncSessionLocal() as session:
            # Check for existing key in the same category
            stmt = select(MemoryEntry).where(
                and_(MemoryEntry.category == category, MemoryEntry.key == key)
            )
            res = await session.execute(stmt)
            existing = res.scalar_one_or_none()

            if existing:
                existing.content = sanitized_content
                existing.tags = list(set((existing.tags or []) + tags))
                existing.relevance_score = max(existing.relevance_score, relevance_score)
                existing.updated_at = datetime.now(timezone.utc)
                await session.commit()
                await session.refresh(existing)
                result = {
                    "memory_id": existing.memory_id,
                    "category": existing.category,
                    "key": existing.key,
                    "content": existing.content,
                    "tags": existing.tags,
                    "relevance_score": existing.relevance_score,
                    "access_count": existing.access_count,
                    "updated_at": existing.updated_at.isoformat(),
                    "redacted_secret": secret_found
                }
            else:
                entry = MemoryEntry(
                    memory_id=memory_id,
                    category=category,
                    key=key,
                    content=sanitized_content,
                    tags=tags,
                    relevance_score=relevance_score,
                    access_count=1,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                session.add(entry)
                await session.commit()
                await session.refresh(entry)
                result = {
                    "memory_id": entry.memory_id,
                    "category": entry.category,
                    "key": entry.key,
                    "content": entry.content,
                    "tags": entry.tags,
                    "relevance_score": entry.relevance_score,
                    "access_count": entry.access_count,
                    "created_at": entry.created_at.isoformat(),
                    "redacted_secret": secret_found
                }

        # Also push to short-term cache
        self.push_short_term({"key": key, "category": category, "content": sanitized_content})
        logger.info(f"Stored memory [{category}]: '{key}' (privacy scrubbed: {secret_found})")
        return result

    async def search_memory(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search stored memories by keyword query with relevance scoring."""
        raw_words = re.findall(r'\b[a-zA-Z0-9_-]+\b', query.lower())
        query_terms = [w for w in raw_words if len(w) > 1]
        if not query_terms:
            return await self.list_memories(category=category, limit=limit)

        async with AsyncSessionLocal() as session:
            stmt = select(MemoryEntry)
            if category and category in self.CATEGORIES:
                stmt = stmt.where(MemoryEntry.category == category)

            # Match against key, content, or tags
            conditions = []
            for term in query_terms:
                conditions.append(MemoryEntry.key.ilike(f"%{term}%"))
                conditions.append(MemoryEntry.content.ilike(f"%{term}%"))
            
            stmt = stmt.where(or_(*conditions))
            stmt = stmt.order_by(MemoryEntry.relevance_score.desc(), MemoryEntry.access_count.desc())
            stmt = stmt.limit(limit)

            res = await session.execute(stmt)
            entries = res.scalars().all()

            results = []
            for e in entries:
                # Increment access count
                e.access_count += 1
                results.append({
                    "memory_id": e.memory_id,
                    "category": e.category,
                    "key": e.key,
                    "content": e.content,
                    "tags": e.tags,
                    "relevance_score": e.relevance_score,
                    "access_count": e.access_count,
                    "updated_at": e.updated_at.isoformat() if e.updated_at else None
                })
            await session.commit()
            return results

    async def get_memory(self, key_or_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific memory entry by memory_id or key."""
        async with AsyncSessionLocal() as session:
            stmt = select(MemoryEntry).where(
                or_(MemoryEntry.memory_id == key_or_id, MemoryEntry.key == key_or_id)
            )
            res = await session.execute(stmt)
            entry = res.scalar_one_or_none()
            if not entry:
                return None
            entry.access_count += 1
            await session.commit()
            return {
                "memory_id": entry.memory_id,
                "category": entry.category,
                "key": entry.key,
                "content": entry.content,
                "tags": entry.tags,
                "relevance_score": entry.relevance_score,
                "access_count": entry.access_count,
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
                "updated_at": entry.updated_at.isoformat() if entry.updated_at else None
            }

    async def delete_memory(self, key_or_id: str) -> bool:
        """Delete a memory entry by memory_id or key."""
        async with AsyncSessionLocal() as session:
            stmt = delete(MemoryEntry).where(
                or_(MemoryEntry.memory_id == key_or_id, MemoryEntry.key == key_or_id)
            )
            res = await session.execute(stmt)
            await session.commit()
            return res.rowcount > 0

    async def list_memories(
        self,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List stored memories, optionally filtered by category."""
        async with AsyncSessionLocal() as session:
            stmt = select(MemoryEntry)
            if category and category in self.CATEGORIES:
                stmt = stmt.where(MemoryEntry.category == category)
            stmt = stmt.order_by(MemoryEntry.updated_at.desc()).limit(limit)
            res = await session.execute(stmt)
            entries = res.scalars().all()
            return [
                {
                    "memory_id": e.memory_id,
                    "category": e.category,
                    "key": e.key,
                    "content": e.content,
                    "tags": e.tags,
                    "relevance_score": e.relevance_score,
                    "access_count": e.access_count,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                    "updated_at": e.updated_at.isoformat() if e.updated_at else None
                }
                for e in entries
            ]

    async def export_memories(self) -> List[Dict[str, Any]]:
        """Export all memory entries for backup or migration."""
        return await self.list_memories(limit=1000)

    async def get_relevant_context(self, prompt: str, limit: int = 5) -> str:
        """Retrieve relevant memory facts and format them as an LLM prompt block."""
        matches = await self.search_memory(prompt, limit=limit)
        if not matches:
            return ""
        lines = ["[Known User Context & Project Memory]:"]
        for m in matches:
            lines.append(f"- ({m['category'].upper()}) {m['key']}: {m['content']}")
        return "\n".join(lines)

    def push_short_term(self, item: Dict[str, Any]):
        """Maintain short-term FIFO conversational context."""
        item["timestamp"] = datetime.now(timezone.utc).isoformat()
        self._short_term_cache.append(item)
        if len(self._short_term_cache) > self._max_short_term:
            self._short_term_cache.pop(0)

    def get_short_term(self) -> List[Dict[str, Any]]:
        """Retrieve current short-term conversational context."""
        return list(self._short_term_cache)

    async def store(
        self,
        key: str,
        value: str,
        category: str = "personal",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convenience alias for add_memory."""
        return await self.add_memory(key=key, content=value, category=category)

    async def retrieve(
        self,
        key: str,
        session_id: Optional[str] = None
    ) -> Optional[str]:
        """Convenience alias for get_memory content."""
        mem = await self.get_memory(key)
        return mem.get("content") if mem else None

    async def get_context(
        self,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Convenience alias for get_short_term conversational context."""
        return self.get_short_term()


memory_manager = MemoryManager()
