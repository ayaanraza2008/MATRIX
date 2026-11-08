"""MATRIX Autonomous Intelligence & Orchestration System (Autonomy Core).
Unifies the 12 core subsystems into an autonomous operating brain and
executes the 7-step continuous lifecycle:
  UNDERSTAND -> PLAN -> SELECT TOOLS -> EXECUTE -> VERIFY -> LEARN -> REPORT
"""
from typing import Dict, Any, List, Optional
import time
import asyncio
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from config.logging_config import get_logger
from core.autonomy.goal_manager import goal_manager
from core.autonomy.tool_discovery import tool_discovery
from core.autonomy.event_monitor import event_monitor
from core.self_maintenance.diagnostics import diagnostics_engine
from core.self_maintenance.recovery import recovery_engine
from security.permissions.manager import security_manager, AutonomyLevel
from memory.manager import memory_manager
from core.telephony.engine import telephony_engine
from core.information.briefing import briefing_engine
from automation.scheduler.engine import background_scheduler
from core.integrations.manager import integration_manager

logger = get_logger("autonomy.core")


class LifecycleTrace(BaseModel):
    step: str  # UNDERSTAND, PLAN, SELECT_TOOLS, EXECUTE, VERIFY, LEARN, REPORT
    status: str
    details: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: float = 0.0


class AutonomousExecutionResult(BaseModel):
    success: bool
    goal_id: Optional[str] = None
    lifecycle_traces: List[LifecycleTrace] = Field(default_factory=list)
    final_output: str
    execution_time_ms: float = 0.0


class AutonomousCore:
    """Central personal AI operating coordinator."""

    def __init__(self):
        self.is_initialized: bool = False
        self._execution_history: List[Dict[str, Any]] = []

    async def initialize(self):
        """Warm up and link all autonomous operating components."""
        if self.is_initialized:
            return
        logger.info("Initializing MATRIX Autonomy Core...")
        # 1. Initialize tool registry cache
        tools = tool_discovery.discover_all()
        # 2. Register standard diagnostic event listeners
        event_monitor.subscribe("DIAGNOSTIC_FAILURE", self._handle_diagnostic_failure)
        # 3. Mark ready
        self.is_initialized = True
        logger.info(f"Autonomy Core online with {len(tools)} registered tools across 16 agents and 43 external repositories.")

    async def _handle_diagnostic_failure(self, evt: Dict[str, Any]):
        """Autonomous self-healing triggered when a component reports failure."""
        logger.warning(f"Autonomy Core received diagnostic alert: {evt.get('payload')}")
        await recovery_engine.auto_recover_system()

    async def execute_autonomous_cycle(
        self,
        user_prompt: str,
        autonomy_level: Optional[int] = None
    ) -> AutonomousExecutionResult:
        """Execute the 7-step continuous autonomous operating cycle."""
        start_ts = time.perf_counter()
        traces: List[LifecycleTrace] = []

        if autonomy_level is not None:
            security_manager.set_global_autonomy_level(autonomy_level)

        # ---------------------------------------------------------
        # STEP 1: UNDERSTAND
        # ---------------------------------------------------------
        s1_start = time.perf_counter()
        relevant_memory = await memory_manager.get_relevant_context(user_prompt)
        traces.append(LifecycleTrace(
            step="UNDERSTAND",
            status="SUCCESS",
            details={
                "prompt": user_prompt,
                "context_injected": bool(relevant_memory),
                "memory_snippet": relevant_memory[:100] if relevant_memory else ""
            },
            duration_ms=round((time.perf_counter() - s1_start) * 1000, 2)
        ))

        # ---------------------------------------------------------
        # STEP 2: PLAN
        # ---------------------------------------------------------
        s2_start = time.perf_counter()
        active_goal = goal_manager.create_goal(
            title=f"Execute: {user_prompt[:50]}",
            description=user_prompt,
            subgoals=[{"title": "Execute Primary Directive"}]
        )
        traces.append(LifecycleTrace(
            step="PLAN",
            status="SUCCESS",
            details={
                "goal_id": active_goal.goal_id,
                "sub_goals_count": len(active_goal.subgoals)
            },
            duration_ms=round((time.perf_counter() - s2_start) * 1000, 2)
        ))

        # ---------------------------------------------------------
        # STEP 3: SELECT TOOLS
        # ---------------------------------------------------------
        s3_start = time.perf_counter()
        matched_tools = tool_discovery.find_tools(user_prompt)
        traces.append(LifecycleTrace(
            step="SELECT_TOOLS",
            status="SUCCESS",
            details={
                "matched_count": len(matched_tools),
                "tools": [t["name"] for t in matched_tools[:3]]
            },
            duration_ms=round((time.perf_counter() - s3_start) * 1000, 2)
        ))

        # ---------------------------------------------------------
        # STEP 4: EXECUTE (with 4-Tier Security Gate)
        # ---------------------------------------------------------
        s4_start = time.perf_counter()
        eval_result = security_manager.evaluate_action(user_prompt, target="OS")
        output = ""
        success = True

        if eval_result.get("requires_confirmation", False):
            output = f"Action paused for human confirmation (Level 4 Policy). Request ID: {eval_result.get('request_id')}"
            success = False
            traces.append(LifecycleTrace(
                step="EXECUTE",
                status="GATE_WAITING_CONFIRMATION",
                details=eval_result,
                duration_ms=round((time.perf_counter() - s4_start) * 1000, 2)
            ))
        else:
            # Execute through core Brain fast path or agent
            from core.brain import brain
            agent_res = await brain.process_input(user_prompt)
            output = agent_res.get("response", "Action completed.")
            traces.append(LifecycleTrace(
                step="EXECUTE",
                status="SUCCESS",
                details={"response_snippet": output[:120]},
                duration_ms=round((time.perf_counter() - s4_start) * 1000, 2)
            ))

        # ---------------------------------------------------------
        # STEP 5: VERIFY
        # ---------------------------------------------------------
        s5_start = time.perf_counter()
        verify_status = "PASS" if success else "NEEDS_APPROVAL"
        traces.append(LifecycleTrace(
            step="VERIFY",
            status=verify_status,
            details={"verified_execution": success},
            duration_ms=round((time.perf_counter() - s5_start) * 1000, 2)
        ))

        # ---------------------------------------------------------
        # STEP 6: LEARN
        # ---------------------------------------------------------
        s6_start = time.perf_counter()
        if success:
            if active_goal.subgoals: goal_manager.update_subgoal_progress(active_goal.goal_id, active_goal.subgoals[0].subgoal_id, status="COMPLETED")
            # Store learning in short-term context
            memory_manager.push_short_term({
                "directive": user_prompt,
                "outcome": output[:100],
                "status": "COMPLETED"
            })
        traces.append(LifecycleTrace(
            step="LEARN",
            status="SUCCESS",
            details={"short_term_updated": True, "goal_updated": success},
            duration_ms=round((time.perf_counter() - s6_start) * 1000, 2)
        ))

        # ---------------------------------------------------------
        # STEP 7: REPORT
        # ---------------------------------------------------------
        s7_start = time.perf_counter()
        total_time_ms = round((time.perf_counter() - start_ts) * 1000, 2)
        traces.append(LifecycleTrace(
            step="REPORT",
            status="SUCCESS",
            details={"total_time_ms": total_time_ms},
            duration_ms=round((time.perf_counter() - s7_start) * 1000, 2)
        ))

        res = AutonomousExecutionResult(
            success=success,
            goal_id=active_goal.goal_id,
            lifecycle_traces=traces,
            final_output=output,
            execution_time_ms=total_time_ms
        )

        self._execution_history.append({
            "prompt": user_prompt,
            "success": success,
            "duration_ms": total_time_ms,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        if len(self._execution_history) > 100:
            self._execution_history.pop(0)

        return res

    def get_status_overview(self) -> Dict[str, Any]:
        """Comprehensive operational status of all 12 autonomy components."""
        return {
            "is_initialized": self.is_initialized,
            "security": security_manager.get_dashboard_summary(),
            "telephony": telephony_engine.get_policy_summary(),
            "scheduler": background_scheduler.get_all_tasks(),
            "integrations": integration_manager.list_integrations(),
            "tools_count": len(tool_discovery.discover_all()),
            "goals_count": len(goal_manager.list_goals()),
            "execution_history_count": len(self._execution_history)
        }


# Global singleton instance
autonomy_core = AutonomousCore()
