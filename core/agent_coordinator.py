"""MATRIX Central Agent Coordinator.
Coordinates multi-agent delegation, concurrent subtask execution, dependency preservation,
result synthesis, conflict detection, and honest execution telemetry.
"""
from typing import Dict, Any, List, Optional, Set
import asyncio
import time
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from core.planner import ExecutionPlan, PlanStep
from core.task_router import task_router
from core.task_state import TaskState
from agents.base_agent import AgentResult
from config.logging_config import get_logger

logger = get_logger("core.agent_coordinator")


class SubtaskExecutionReport(BaseModel):
    step_id: int
    title: str
    agent_name: str
    tool_name: str
    status: str
    latency_ms: float
    result: Optional[Any] = None
    error: Optional[str] = None
    conflicts_detected: List[str] = Field(default_factory=list)


class CoordinatorResult(BaseModel):
    plan_id: str
    overall_status: str
    total_steps: int
    completed_steps: int
    failed_steps: int
    subtask_reports: List[SubtaskExecutionReport] = Field(default_factory=list)
    combined_output: Dict[str, Any] = Field(default_factory=dict)
    conflicts: List[str] = Field(default_factory=list)
    total_latency_ms: float = 0.0


class AgentCoordinator:
    """Orchestrates multi-agent execution with concurrent subtask dispatch and conflict detection."""

    def __init__(self):
        self._active_agents: Dict[str, Dict[str, Any]] = {}
        self._execution_history: List[CoordinatorResult] = []

    def get_agent_dashboard(self) -> Dict[str, Any]:
        """Return real-time agent activity telemetry for the dashboard UI."""
        return {
            "timestamp": time.time(),
            "registered_agents_count": len(task_router._agents),
            "agents": {
                name: {
                    "description": ag.description,
                    "max_autonomy": ag.max_autonomy_level,
                    "status": "IDLE" if name not in self._active_agents else "BUSY",
                    "tools": ag.discover_tools()
                }
                for name, ag in task_router._agents.items()
            },
            "recent_tasks_count": len(self._execution_history)
        }

    async def execute_plan_concurrent(
        self,
        plan: ExecutionPlan,
        progress_callback: Optional[callable] = None
    ) -> CoordinatorResult:
        """Execute plan by waves: independent subtasks run concurrently via asyncio.gather(),
        while dependent subtasks wait for prerequisites.
        """
        start_time = time.perf_counter()
        reports: List[SubtaskExecutionReport] = []
        combined_data: Dict[str, Any] = {}
        conflicts: List[str] = []

        completed_ids: Set[int] = set()
        remaining_steps = list(plan.steps)

        while remaining_steps:
            # Find all steps whose dependencies have succeeded
            ready_wave = [
                s for s in remaining_steps
                if not s.dependencies or all(dep in completed_ids for dep in s.dependencies)
            ]

            if not ready_wave:
                # Deadlock or cyclic dependency detected
                deadlock_msg = f"Dependency deadlock detected for remaining steps: {[s.step_id for s in remaining_steps]}"
                logger.error(deadlock_msg)
                conflicts.append(deadlock_msg)
                break

            # Execute ready wave concurrently
            wave_tasks = [self._execute_single_step(s, progress_callback) for s in ready_wave]
            wave_results = await asyncio.gather(*wave_tasks)

            for step, res, latency in wave_results:
                report = SubtaskExecutionReport(
                    step_id=step.step_id,
                    title=step.title,
                    agent_name=step.agent_name,
                    tool_name=step.tool_name,
                    status="COMPLETED" if res.success else "FAILED",
                    latency_ms=round(latency, 2),
                    result=res.data,
                    error=res.error
                )
                reports.append(report)

                if res.success:
                    completed_ids.add(step.step_id)
                    combined_data[f"step_{step.step_id}_{step.agent_name}"] = res.data
                else:
                    conflicts.append(f"Step {step.step_id} ({step.title}) failed: {res.error}")

            # Remove finished steps
            for s in ready_wave:
                remaining_steps.remove(s)

        total_latency = (time.perf_counter() - start_time) * 1000
        completed_count = len(completed_ids)
        total_count = len(plan.steps)
        failed_count = total_count - completed_count

        overall = "COMPLETED" if failed_count == 0 else ("PARTIAL" if completed_count > 0 else "FAILED")

        coordinator_res = CoordinatorResult(
            plan_id=plan.plan_id,
            overall_status=overall,
            total_steps=total_count,
            completed_steps=completed_count,
            failed_steps=failed_count,
            subtask_reports=reports,
            combined_output=combined_data,
            conflicts=conflicts,
            total_latency_ms=round(total_latency, 2)
        )
        self._execution_history.append(coordinator_res)
        return coordinator_res

    async def _execute_single_step(self, step: PlanStep, callback: Optional[callable]):
        t0 = time.perf_counter()
        agent = task_router.get_agent(step.agent_name)
        if not agent:
            res = AgentResult(success=False, agent_name=step.agent_name, action_taken=step.tool_name, error=f"Unknown agent: {step.agent_name}")
            return step, res, (time.perf_counter() - t0) * 1000

        self._active_agents[step.agent_name] = {"step_id": step.step_id, "start": t0}
        if callback:
            try:
                callback({"event": "STEP_STARTED", "step_id": step.step_id, "agent": step.agent_name})
            except Exception:
                pass

        try:
            res = await agent.run_with_timeout(step.tool_name, step.arguments)
        except Exception as ex:
            res = AgentResult(success=False, agent_name=step.agent_name, action_taken=step.tool_name, error=str(ex))
        finally:
            self._active_agents.pop(step.agent_name, None)

        dt = (time.perf_counter() - t0) * 1000
        return step, res, dt


# Global Agent Coordinator singleton
agent_coordinator = AgentCoordinator()
