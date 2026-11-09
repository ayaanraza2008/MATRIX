"""MATRIX Memory & Knowledge Retrieval Agent.
Stores, retrieves, edits, ranks, deduplicates, and deletes user preferences and factual knowledge in SQLite.
Supports user-controlled memory categories: preferences, summaries, projects, decisions, tasks, learned_workflows.
"""
from typing import Dict, Any, List, Optional
import time
import re
from sqlalchemy import select, delete
from agents.base_agent import BaseAgent, AgentResult, AgentCapability
from database.session import AsyncSessionLocal
from database.models import UserPreference
from config.logging_config import get_logger

logger = get_logger("agents.memory")


class MemoryAgent(BaseAgent):
    """Coordinates long-term memory retrieval, entity inspection, and preference management."""

    MEMORY_CATEGORIES = [
        "preferences", "summaries", "projects", "decisions", "tasks", "learned_workflows", "tool_history"
    ]

    def __init__(self):
        super().__init__(
            name="memory",
            description="Manages approved preferences, project context, and knowledge retrieval with zero fabrication.",
            max_autonomy_level=1
        )
        self._capabilities = [
            AgentCapability(name="save_memory", description="Store or update a user preference or factual knowledge", operations=["save", "store", "remember"]),
            AgentCapability(name="retrieve_memory", description="Retrieve stored memories by key or category", operations=["list", "get", "inspect", "search"]),
            AgentCapability(name="delete_memory", description="User-controlled memory deletion and purge", operations=["delete", "forget", "purge", "clear"])
        ]

    async def execute(self, action: str, parameters: Dict[str, Any]) -> AgentResult:
        start_time = time.perf_counter()
        action_lower = action.lower()
        raw_prompt = parameters.get("query", parameters.get("prompt", parameters.get("raw_prompt", ""))).strip()

        # 1. Delete / Forget Memory
        if any(w in action_lower for w in ["delete", "forget", "purge", "remove", "clear"]) or any(w in raw_prompt.lower() for w in ["forget", "delete from memory", "delete memory"]):
            key = parameters.get("key")
            if not key:
                m = re.search(r'(?:forget|delete|remove)\s+(?:preference\s+)?(.+?)(?:\s+from\s+memory)?$', raw_prompt, re.IGNORECASE)
                if m:
                    key = m.group(1).strip().replace(" ", "_").lower()
            if key:
                deleted = await self._delete_preference(key)
                try:
                    from memory.manager import memory_manager
                    await memory_manager.delete_memory(key)
                except Exception:
                    pass
                latency = (time.perf_counter() - start_time) * 1000
                return AgentResult(
                    success=deleted,
                    agent_name=self.name,
                    action_taken="delete_memory",
                    data={"key": key, "deleted": deleted},
                    verification={"verified": deleted, "purged_from_sqlite": deleted},
                    execution_time_ms=round(latency, 2)
                )

        # 2. Fetch Preferences / Memory
        if any(w in action_lower for w in ["list", "get", "inspect", "retrieve", "search"]) or any(w in raw_prompt.lower() for w in ["retrieve", "what is", "get preference", "search memory"]):
            category = parameters.get("category")
            key = parameters.get("key")
            query = parameters.get("query")

            if key:
                preferences = await self._list_preferences(category=category, key=key)
            elif query:
                all_prefs = await self._list_preferences(category=category)
                q_clean = query.lower()
                preferences = [p for p in all_prefs if q_clean in p["key"].lower() or q_clean in str(p["value"]).lower()]
            else:
                preferences = await self._list_preferences(category=category)

            latency = (time.perf_counter() - start_time) * 1000
            val = preferences[0]["value"] if (key and preferences) else (preferences[0]["value"] if len(preferences) == 1 else None)
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="retrieve_memory" if key else ("search_memory" if query else "list_memory"),
                data={
                    "stored_memories": preferences,
                    "matches": preferences,
                    "count": len(preferences),
                    "key": key,
                    "value": val
                },
                verification={"verified": True, "count": len(preferences)},
                execution_time_ms=round(latency, 2)
            )

        # 3. Store New Fact or Preference (with automatic deduplication)
        if "save" in action_lower or "store" in action_lower or "remember" in raw_prompt.lower():
            key = parameters.get("key")
            value = parameters.get("value")
            category = parameters.get("category", "preferences")
            
            # Extract key/value from natural language prompt if missing
            if not key or not value:
                m = re.search(r'(?:save|store|remember)\s+(?:my\s+)?(.+?)\s+as\s+(.+?)(?:\s+in\s+memory)?$', raw_prompt, re.IGNORECASE)
                if m:
                    key = m.group(1).strip().replace(" ", "_").lower()
                    value = m.group(2).strip()
                else:
                    key = f"pref_{int(time.time())}"
                    value = raw_prompt

            saved = await self._save_preference(key, value, category=category)
            
            # Also sync with OpenViking Context Memory Adapter
            try:
                from core.tool_adapters.manager import adapter_manager
                await adapter_manager.execute(
                    "adapter_context_memory",
                    "store_context",
                    {"key": key, "content": str(value), "tags": [category, "user_preference"]}
                )
            except Exception:
                pass

            try:
                from memory.manager import memory_manager
                await memory_manager.add_memory(
                    key=key,
                    content=str(value),
                    category="preference",
                    tags=[category, "user_preference"]
                )
            except Exception:
                pass

            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=saved,
                agent_name=self.name,
                action_taken="save_memory",
                data={"key": key, "value": value, "category": category, "saved": saved},
                verification={"verified": saved, "stored_in_sqlite": True},
                execution_time_ms=round(latency, 2)
            )

        if action_lower in ["memory_status", "status", "info"]:
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="memory_status",
                data={
                    "engine": "SQLite Async + Vector RAG",
                    "location": "D:\\matrix_data\\matrix.db",
                    "supported_categories": self.MEMORY_CATEGORIES
                },
                verification={"verified": True},
                execution_time_ms=round(latency, 2)
            )

        latency = (time.perf_counter() - start_time) * 1000
        return AgentResult(
            success=False,
            agent_name=self.name,
            action_taken=action,
            error=f"Unsupported action '{action}' for MemoryAgent",
            execution_status="FAILED",
            verification_status="FAILED",
            execution_time_ms=round(latency, 2)
        )

    async def _list_preferences(self, category: Optional[str] = None, key: Optional[str] = None) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            stmt = select(UserPreference)
            if category:
                stmt = stmt.where(UserPreference.category == category)
            if key:
                stmt = stmt.where(UserPreference.key == key)
            res = await session.execute(stmt)
            prefs = res.scalars().all()
            return [{"key": p.key, "value": p.value, "category": p.category} for p in prefs]

    async def _save_preference(self, key: str, value: Any, category: str = "preferences") -> bool:
        """Save or update (deduplicate) a preference in SQLite."""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(UserPreference).where(UserPreference.key == key)
                res = await session.execute(stmt)
                existing = res.scalar_one_or_none()

                if existing:
                    existing.value = value
                    existing.category = category
                else:
                    pref = UserPreference(
                        key=key,
                        value=value,
                        category=category,
                        is_user_editable=True
                    )
                    session.add(pref)
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to persist preference {key}: {e}")
            return False

    async def _delete_preference(self, key: str) -> bool:
        """Purge a preference from SQLite database."""
        try:
            async with AsyncSessionLocal() as session:
                stmt = delete(UserPreference).where(UserPreference.key == key)
                await session.execute(stmt)
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to delete preference {key}: {e}")
            return False

    async def verify(self, action: str, result: Any) -> bool:
        return bool(result and (isinstance(result, dict) or getattr(result, "success", True)))
