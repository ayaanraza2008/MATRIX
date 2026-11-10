"""MATRIX Autonomous Intelligence & Orchestration System (Autonomy Core).
Unifies the 16 core agents and external subsystems into an autonomous operating brain and
executes the 12-step continuous JARVIS lifecycle:
  UNDERSTAND -> CONTEXT -> PLAN -> SELECT AGENTS -> SELECT TOOLS -> CHECK AUTHORIZATION ->
  EXECUTE -> OBSERVE -> VERIFY -> RECOVER -> LEARN -> REPORT
"""
from typing import Dict, Any, List, Optional
import time
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from config.logging_config import get_logger
from core.autonomy.goal_manager import goal_manager
from core.autonomy.tool_discovery import tool_discovery
from core.autonomy.event_monitor import event_monitor
from core.self_maintenance.recovery import recovery_engine
from security.permissions.manager import security_manager
from security.permissions.authorization_center import authorization_center
from memory.manager import memory_manager
from core.telephony.engine import telephony_engine
from automation.scheduler.engine import background_scheduler
from core.integrations.manager import integration_manager
from core.intent_engine import intent_engine
from core.reasoning_engine import reasoning_engine

logger = get_logger("autonomy.core")


class LifecycleTrace(BaseModel):
    step: str  # UNDERSTAND, CONTEXT, PLAN, SELECT_AGENTS, SELECT_TOOLS, CHECK_AUTHORIZATION, EXECUTE, OBSERVE, VERIFY, RECOVER, LEARN, REPORT
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
    """Central personal AI operating coordinator executing high-level autonomous directives."""

    def __init__(self):
        self.is_initialized: bool = False
        self._execution_history: List[Dict[str, Any]] = []

    async def initialize(self):
        """Warm up and link all autonomous operating components."""
        if self.is_initialized:
            return
        logger.info("Initializing MATRIX Autonomy Core...")
        tools = tool_discovery.discover_all()
        event_monitor.subscribe("DIAGNOSTIC_FAILURE", self._handle_diagnostic_failure)
        self.is_initialized = True
        logger.info(f"Autonomy Core online with {len(tools)} registered tools across 16 agents.")

    async def _handle_diagnostic_failure(self, evt: Dict[str, Any]):
        """Autonomous self-healing triggered when a component reports failure."""
        logger.warning(f"Autonomy Core received diagnostic alert: {evt.get('payload')}")
        await recovery_engine.auto_recover_system()

    async def execute_autonomous_cycle(
        self,
        user_prompt: str,
        autonomy_level: Optional[int] = None,
        session_id: str = "sess_autonomy_core"
    ) -> AutonomousExecutionResult:
        """Execute the full 12-step continuous autonomous operating cycle."""
        start_ts = time.perf_counter()
        traces: List[LifecycleTrace] = []

        if autonomy_level is not None:
            security_manager.set_global_autonomy_level(autonomy_level)

        # ---------------------------------------------------------
        # STAGE 1: UNDERSTAND
        # ---------------------------------------------------------
        s1_start = time.perf_counter()
        intent = intent_engine.classify(user_prompt)
        traces.append(LifecycleTrace(
            step="UNDERSTAND",
            status="SUCCESS",
            details={
                "intent_type": getattr(intent.intent_type, "value", str(intent.intent_type)),
                "confidence": intent.confidence,
                "target_agent": intent.target_agent,
                "action": intent.action
            },
            duration_ms=round((time.perf_counter() - s1_start) * 1000, 2)
        ))

        # ---------------------------------------------------------
        # STAGE 2: CONTEXT
        # ---------------------------------------------------------
        s2_start = time.perf_counter()
        relevant_memory = await memory_manager.get_relevant_context(user_prompt)
        traces.append(LifecycleTrace(
            step="CONTEXT",
            status="SUCCESS",
            details={
                "context_injected": bool(relevant_memory),
                "memory_snippet": relevant_memory[:120] if relevant_memory else "",
                "session_id": session_id
            },
            duration_ms=round((time.perf_counter() - s2_start) * 1000, 2)
        ))

        # ---------------------------------------------------------
        # STAGE 3: PLAN
        # ---------------------------------------------------------
        s3_start = time.perf_counter()
        plan = reasoning_engine.create_plan(intent)
        active_goal = goal_manager.create_goal(
            title=plan.title or f"Directive: {user_prompt[:40]}",
            description=user_prompt,
            subgoals=[{"title": s.title} for s in plan.steps] if plan.steps else [{"title": "Execute Directive"}]
        )
        traces.append(LifecycleTrace(
            step="PLAN",
            status="SUCCESS",
            details={
                "goal_id": active_goal.goal_id,
                "plan_id": plan.plan_id,
                "total_steps": len(plan.steps),
                "risk_level": plan.max_risk_level
            },
            duration_ms=round((time.perf_counter() - s3_start) * 1000, 2)
        ))

        # ---------------------------------------------------------
        # STAGE 4: SELECT AGENTS
        # ---------------------------------------------------------
        s4_start = time.perf_counter()
        selected_agents = list({s.agent_name for s in plan.steps}) if plan.steps else [intent.target_agent]
        traces.append(LifecycleTrace(
            step="SELECT_AGENTS",
            status="SUCCESS",
            details={"agents": selected_agents},
            duration_ms=round((time.perf_counter() - s4_start) * 1000, 2)
        ))

        # ---------------------------------------------------------
        # STAGE 5: SELECT TOOLS
        # ---------------------------------------------------------
        s5_start = time.perf_counter()
        selected_tools = [f"{s.agent_name}.{s.tool_name}" for s in plan.steps] if plan.steps else [f"{intent.target_agent}.{intent.action}"]
        discovered = tool_discovery.find_tools(user_prompt)
        traces.append(LifecycleTrace(
            step="SELECT_TOOLS",
            status="SUCCESS",
            details={
                "selected_tools": selected_tools,
                "matched_discovered_count": len(discovered)
            },
            duration_ms=round((time.perf_counter() - s5_start) * 1000, 2)
        ))

        # ---------------------------------------------------------
        # STAGE 6: CHECK AUTHORIZATION
        # ---------------------------------------------------------
        s6_start = time.perf_counter()
        can_run, profile_name, auth_reason = authorization_center.evaluate_authorization(
            action=intent.action or user_prompt,
            category="windows_permissions",
            details={"risk_level": plan.max_risk_level}
        )
        traces.append(LifecycleTrace(
            step="CHECK_AUTHORIZATION",
            status="AUTHORIZED" if can_run else "CONFIRMATION_REQUIRED",
            details={
                "profile": profile_name,
                "reason": auth_reason,
                "can_proceed": can_run
            },
            duration_ms=round((time.perf_counter() - s6_start) * 1000, 2)
        ))

        output = ""
        success = True

        if not can_run:
            output = f"Action paused: {auth_reason}"
            success = False
            # Record remaining stages as gated
            for stg in ["EXECUTE", "OBSERVE", "VERIFY", "RECOVER"]:
                traces.append(LifecycleTrace(step=stg, status="GATED_BY_AUTHORIZATION", duration_ms=0.0))
        else:
            # ---------------------------------------------------------
            # STAGE 7: EXECUTE
            # ---------------------------------------------------------
            s7_start = time.perf_counter()
            from core.brain import brain
            agent_res = await brain.process_user_request(session_id=session_id, user_prompt=user_prompt)
            output = agent_res.get("response", "Action completed.")
            success = not bool(agent_res.get("error"))
            traces.append(LifecycleTrace(
                step="EXECUTE",
                status="SUCCESS" if success else "FAILED",
                details={
                    "response_id": agent_res.get("response_id"),
                    "output_snippet": output[:120]
                },
                duration_ms=round((time.perf_counter() - s7_start) * 1000, 2)
            ))

            # ---------------------------------------------------------
            # STAGE 8: OBSERVE
            # ---------------------------------------------------------
            s8_start = time.perf_counter()
            traces.append(LifecycleTrace(
                step="OBSERVE",
                status="SUCCESS",
                details={
                    "has_output": bool(output),
                    "character_count": len(output),
                    "subgoals_active": len(active_goal.subgoals)
                },
                duration_ms=round((time.perf_counter() - s8_start) * 1000, 2)
            ))

            # ---------------------------------------------------------
            # STAGE 9: VERIFY
            # ---------------------------------------------------------
            s9_start = time.perf_counter()
            verify_status = "VERIFIED" if success else "FAILED"
            traces.append(LifecycleTrace(
                step="VERIFY",
                status=verify_status,
                details={"verified_execution": success},
                duration_ms=round((time.perf_counter() - s9_start) * 1000, 2)
            ))

            # ---------------------------------------------------------
            # STAGE 10: RECOVER
            # ---------------------------------------------------------
            s10_start = time.perf_counter()
            if not success:
                logger.warning(f"Execution failed; triggering autonomous recovery diagnostics...")
                await recovery_engine.auto_recover_system()
                recover_status = "RECOVERY_ATTEMPTED"
            else:
                recover_status = "NOT_NEEDED"
            traces.append(LifecycleTrace(
                step="RECOVER",
                status=recover_status,
                details={"recovered": success},
                duration_ms=round((time.perf_counter() - s10_start) * 1000, 2)
            ))

        # ---------------------------------------------------------
        # STAGE 11: LEARN
        # ---------------------------------------------------------
        s11_start = time.perf_counter()
        if success:
            if active_goal.subgoals:
                goal_manager.update_subgoal_progress(active_goal.goal_id, active_goal.subgoals[0].subgoal_id, status="COMPLETED")
            memory_manager.push_short_term({
                "directive": user_prompt,
                "outcome": output[:100],
                "status": "COMPLETED"
            })
        traces.append(LifecycleTrace(
            step="LEARN",
            status="SUCCESS",
            details={"short_term_updated": True, "goal_updated": success},
            duration_ms=round((time.perf_counter() - s11_start) * 1000, 2)
        ))

        # ---------------------------------------------------------
        # STAGE 12: REPORT
        # ---------------------------------------------------------
        s12_start = time.perf_counter()
        total_time_ms = round((time.perf_counter() - start_ts) * 1000, 2)
        traces.append(LifecycleTrace(
            step="REPORT",
            status="SUCCESS",
            details={"total_time_ms": total_time_ms, "final_status": "COMPLETED" if success else "IMPAIRED"},
            duration_ms=round((time.perf_counter() - s12_start) * 1000, 2)
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
        """Comprehensive operational status of all autonomy components."""
        return {
            "is_initialized": self.is_initialized,
            "security": security_manager.get_dashboard_summary(),
            "authorization_center": authorization_center.get_authorization_overview(),
            "telephony": telephony_engine.get_policy_summary(),
            "scheduler": background_scheduler.get_all_tasks(),
            "integrations": integration_manager.list_integrations(),
            "tools_count": len(tool_discovery.discover_all()),
            "goals_count": len(goal_manager.list_goals()),
            "execution_history_count": len(self._execution_history)
        }


# Global singleton instance
autonomy_core = AutonomousCore()
