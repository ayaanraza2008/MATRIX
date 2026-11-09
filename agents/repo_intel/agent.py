"""MATRIX Repository Intelligence Agent.
Discovers, evaluates, selects, adapts, and executes capabilities from the verified 65 GitHub Repositories.
"""
from typing import Dict, Any, List
import time
from agents.base_agent import BaseAgent, AgentResult, AgentCapability
from core.repository_intelligence.engine import repo_intelligence
from core.tool_adapters.manager import adapter_manager
from core.capability_registry.registry import capability_registry
from core.reference_knowledge.engine import reference_knowledge_engine
from core.repository_intelligence.hardware_guard import hardware_guard


class RepoIntelAgent(BaseAgent):
    """Assists with autonomous discovery, tool selection, gap analysis, and repository adapter execution."""

    def __init__(self):
        super().__init__(
            name="repo_intel",
            description="Analyzes the verified 65 GitHub repositories, selects tools autonomously, and manages adapters.",
            max_autonomy_level=2
        )
        self._capabilities = [
            AgentCapability(name="tool_selection", description="Autonomously map user intents to specialized tools", operations=["select_tool", "resolve_task"]),
            AgentCapability(name="gap_detection", description="Detect missing system capabilities and recommend adapters", operations=["detect_gap"]),
            AgentCapability(name="inventory_query", description="Search and inspect catalog of 65 verified repositories", operations=["query_inventory", "search", "inventory", "list"]),
            AgentCapability(name="system_summary", description="Provide high-level telemetry and status of repository ecosystems", operations=["get_summary", "summary"])
        ]

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

        elif act == "chain_adapters":
            # Multi-repository autonomous pipeline execution
            pipeline_steps = parameters.get("steps", [])
            results = []
            chain_success = True
            shared_context = parameters.get("initial_context", {})

            for idx, step in enumerate(pipeline_steps):
                aid = step.get("adapter_id", "")
                op = step.get("operation", "")
                # Step explicit parameters take precedence over inherited context
                params = dict(shared_context)
                params.update(step.get("parameters", {}))
                step_res = await adapter_manager.execute(aid, op, params, is_user_confirmed=True)
                results.append({
                    "step_index": idx + 1,
                    "adapter_id": aid,
                    "operation": op,
                    "success": step_res.success,
                    "data": step_res.data,
                    "execution_time_ms": step_res.execution_time_ms
                })
                if step_res.success and isinstance(step_res.data, dict):
                    shared_context.update(step_res.data)
                elif not step_res.success:
                    chain_success = False
                    break

            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=chain_success,
                agent_name=self.name,
                action_taken="chain_adapters",
                data={"pipeline_steps": results, "final_context": shared_context},
                verification={"pipeline_completed": chain_success, "steps_executed": len(results)},
                execution_time_ms=round(latency, 2)
            )

        elif act == "query_reference":
            query = parameters.get("query", "")
            cat = parameters.get("category")
            res = reference_knowledge_engine.query_reference_catalog(query, category=cat)
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="query_reference",
                data=res,
                verification={"reference_queried": True},
                execution_time_ms=round(latency, 2)
            )

        elif act == "assess_hardware":
            repo_name = parameters.get("repo_name", "")
            if repo_name:
                assess = hardware_guard.assess_repository(repo_name)
                data = {"assessment": assess.model_dump() if assess else None}
            else:
                all_assess = hardware_guard.get_all_incompatible_assessments()
                data = {"assessments": {k: v.model_dump() for k, v in all_assess.items()}}
            data["host_profile"] = hardware_guard.profile.model_dump()
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="assess_hardware",
                data=data,
                verification={"hardware_assessed": True},
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

        elif act in ["query_inventory", "search", "inventory", "list", "query"]:
            # Query repository inventory
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

        else:
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken=action,
                error=f"Unsupported action '{action}' for RepoIntelAgent",
                execution_status="FAILED",
                verification_status="FAILED",
                execution_time_ms=round(latency, 2)
            )

    async def verify(self, action: str, result: Any) -> bool:
        return bool(result and getattr(result, "success", False))
