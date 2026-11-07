"""MATRIX Repository Intelligence Agent.
Discovers, evaluates, selects, adapts, and executes capabilities from the verified 65 GitHub Repositories.
"""
from typing import Dict, Any, List
import time
from agents.base_agent import BaseAgent, AgentResult
from core.repository_intelligence.engine import repo_intelligence
from core.tool_adapters.manager import adapter_manager
from core.capability_registry.registry import capability_registry


class RepoIntelAgent(BaseAgent):
    """Assists with autonomous discovery, tool selection, gap analysis, and repository adapter execution."""

    def __init__(self):
        super().__init__(
            name="repo_intel",
            description="Analyzes the verified 65 GitHub repositories, selects tools autonomously, and manages adapters.",
            max_autonomy_level=2
        )

    async def execute(self, action: str, parameters: Dict[str, Any]) -> AgentResult:
        start_time = time.perf_counter()
        act = action.lower().strip()

        if act == "select_tool" or act == "resolve_task":
            task_desc = parameters.get("task_description") or parameters.get("query", "")
            selection = repo_intelligence.select_best_tool(task_desc)
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="select_tool",
                data=selection.model_dump(),
                verification={"tool_selected": bool(selection.selected_tool_id)},
                execution_time_ms=round(latency, 2)
            )

        elif act == "detect_gap":
            prompt = parameters.get("prompt") or parameters.get("task", "")
            gap = repo_intelligence.detect_capability_gap(prompt)
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="detect_gap",
                data=gap.model_dump(),
                verification={"gap_evaluated": True},
                execution_time_ms=round(latency, 2)
            )

        elif act == "execute_adapter":
            adapter_id = parameters.get("adapter_id", "")
            operation = parameters.get("operation", "")
            params = parameters.get("parameters", {})
            confirmed = parameters.get("is_user_confirmed", False)
            res = await adapter_manager.execute(adapter_id, operation, params, is_user_confirmed=confirmed)
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=res.success,
                agent_name=self.name,
                action_taken=f"{adapter_id}:{operation}",
                data=res.data,
                verification=res.verification,
                error=res.error,
                execution_time_ms=round(latency, 2)
            )

        elif act == "get_summary":
            summary = repo_intelligence.get_summary()
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="get_summary",
                data=summary,
                verification={"summary_ready": True},
                execution_time_ms=round(latency, 2)
            )

        else:
            # Default: query repository inventory
            query = parameters.get("query", "")
            category = parameters.get("category")
            matches = repo_intelligence.search_repositories(query, category=category)
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="query_inventory",
                data={
                    "total_cataloged": len(repo_intelligence.list_all_evaluations()),
                    "matched_count": len(matches),
                    "repositories": [m.model_dump() for m in matches[:15]]
                },
                verification={"search_completed": True},
                execution_time_ms=round(latency, 2)
            )

    async def verify(self, action: str, result: Any) -> bool:
        return bool(result and getattr(result, "success", False))
