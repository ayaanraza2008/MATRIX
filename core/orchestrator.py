"""MATRIX Central Multi-Agent Autonomous Orchestrator.
Coordinates the execution pipeline:
OBSERVE -> UNDERSTAND -> PLAN -> AUTHORIZE -> EXECUTE -> VERIFY -> RECOVER -> REPORT
Features persistent checkpoints, recoverable retries, real-time telemetry events, and policy gates.
"""
from typing import Dict, Any, List, Optional, Callable
import time
import asyncio
from core.intent_engine import intent_engine, ParsedIntent
from core.reasoning_engine import reasoning_engine
from core.planner import ExecutionPlan, PlanStep
from core.task_router import task_router
from core.response_generator import response_generator
from agents.base_agent import AgentResult
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("core.orchestrator")


class OrchestrationResult:
    def __init__(
        self,
        plan: ExecutionPlan,
        results: List[AgentResult],
        response_text: str,
        total_time_ms: float,
        recovered_errors: int = 0
    ):
        self.plan = plan
        self.results = results
        self.response_text = response_text
        self.total_time_ms = total_time_ms
        self.recovered_errors = recovered_errors


class Orchestrator:
    """Autonomous engine for planning, policy gating, delegating, verifying, and recovering multi-agent tasks."""

    def __init__(self):
        self._progress_subscribers: List[Callable[[Dict[str, Any]], Any]] = []
        self._cancel_requested: bool = False

    def subscribe_progress(self, callback: Callable[[Dict[str, Any]], Any]):
        """Register a callback for real-time task progress events."""
        if callback not in self._progress_subscribers:
            self._progress_subscribers.append(callback)

    def unsubscribe_progress(self, callback: Callable[[Dict[str, Any]], Any]):
        if callback in self._progress_subscribers:
            self._progress_subscribers.remove(callback)

    async def _emit_progress(self, event_type: str, data: Dict[str, Any]):
        """Broadcast progress telemetry to UI and hands-free manager."""
        payload = {"type": event_type, "timestamp": time.time(), **data}
        for sub in list(self._progress_subscribers):
            try:
                res = sub(payload)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                logger.debug(f"Progress subscriber error: {e}")

    def cancel_active(self):
        """Emergency stop: Immediately cancel running orchestration."""
        self._cancel_requested = True
        logger.warning("Emergency stop requested in Orchestrator.")

    async def _log_audit_checkpoint(self, action: str, details: str, status: str = "COMPLETED"):
        """Save execution checkpoint to SQLite database."""
        try:
            from database.session import AsyncSessionLocal
            from sqlalchemy import text
            from datetime import datetime, timezone
            async with AsyncSessionLocal() as session:
                await session.execute(
                    text(
                        "INSERT INTO audit_logs (event_type, risk_level, tool_name, actor, action_summary, status, timestamp) "
                        "VALUES (:evt, :risk, :tool, :act, :summary, :stat, :ts)"
                    ),
                    {
                        "evt": "ORCHESTRATION_CHECKPOINT",
                        "risk": 1,
                        "tool": action,
                        "act": "orchestrator",
                        "summary": details,
                        "stat": status,
                        "ts": datetime.now(timezone.utc)
                    }
                )
                await session.commit()
        except Exception as e:
            logger.debug(f"Could not write audit log: {e}")

    async def execute_request(self, prompt: str) -> OrchestrationResult:
        start_time = time.perf_counter()
        self._cancel_requested = False

        # 1. OBSERVE & UNDERSTAND: Intent Extraction
        intent = intent_engine.classify(prompt)
        logger.info(f"Intent classified: {intent.intent_type.value} -> target agent: {intent.target_agent}")
        await self._emit_progress("AGENT_SELECTED", {
            "agent": intent.target_agent,
            "intent": intent.intent_type.value
        })

        # 2. PLAN: Formulate multi-step ExecutionPlan
        plan = reasoning_engine.create_plan(intent)
        total_steps = len(plan.steps)
        await self._emit_progress("TASK_PROGRESS", {
            "status": "PLAN_CREATED",
            "title": plan.title,
            "total_steps": total_steps
        })

        # 3. AUTHORIZE: Policy Gate Check
        if plan.requires_human_approval:
            logger.warning(f"Plan '{plan.title}' blocked: Requires human authorization (Risk Level {plan.max_risk_level})")
            await self._log_audit_checkpoint("SECURITY_GATE_BLOCK", f"Plan '{plan.title}' blocked for high risk", "BLOCKED")
            return OrchestrationResult(
                plan=plan,
                results=[],
                response_text=(
                    f"Security policy requires explicit authorization (Risk Level {plan.max_risk_level}). "
                    f"Please confirm execution of '{plan.title}'."
                ),
                total_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

        # 4. EXECUTE, VERIFY & RECOVER
        results: List[AgentResult] = []
        plan.status = "RUNNING"
        recovered_errors = 0

        for idx, step in enumerate(plan.steps, start=1):
            if self._cancel_requested:
                plan.status = "CANCELLED"
                logger.warning(f"Orchestration cancelled before step {step.step_id}.")
                break

            plan.mark_step_running(step.step_id)
            await self._emit_progress("TASK_PROGRESS", {
                "step_id": step.step_id,
                "step_number": idx,
                "total_steps": total_steps,
                "title": step.title,
                "agent": step.agent_name,
                "action": step.tool_name
            })

            # Execute with automatic retry / recovery
            max_retries = 2
            res: Optional[AgentResult] = None
            for attempt in range(max_retries):
                try:
                    res = await task_router.dispatch(
                        agent_name=step.agent_name,
                        action=step.tool_name,
                        parameters=step.arguments
                    )
                    if res.success:
                        break
                    else:
                        logger.warning(f"Step {step.step_id} attempt {attempt + 1} failed: {res.error}")
                        recovered_errors += 1
                        await asyncio.sleep(0.3)
                except Exception as ex:
                    logger.warning(f"Step {step.step_id} exception on attempt {attempt + 1}: {ex}")
                    res = AgentResult(success=False, error=str(ex))
                    recovered_errors += 1
                    await asyncio.sleep(0.3)

            if res is None:
                res = AgentResult(success=False, error="Action timed out or dispatch failed.")

            results.append(res)

            # VERIFY step output
            if res.success:
                plan.mark_step_completed(step.step_id, result=res.data)
                await self._log_audit_checkpoint(
                    f"{step.agent_name}.{step.tool_name}",
                    f"Step {idx}/{total_steps} completed: {step.title}",
                    "SUCCESS"
                )
            else:
                plan.mark_step_failed(step.step_id, error=res.error or "Action verification failed")
                await self._log_audit_checkpoint(
                    f"{step.agent_name}.{step.tool_name}",
                    f"Step {idx}/{total_steps} failed: {res.error}",
                    "FAILED"
                )
                logger.error(f"Step {step.step_id} ({step.title}) failed permanently: {res.error}")
                break

        if plan.status not in ["FAILED", "CANCELLED"]:
            plan.status = "COMPLETED"

        # 5. REPORT: Unified response synthesis
        response_text = response_generator.format_agent_response(results, prompt)
        total_time = (time.perf_counter() - start_time) * 1000

        await self._emit_progress("TASK_COMPLETED", {
            "status": plan.status,
            "total_time_ms": round(total_time, 2),
            "recovered_errors": recovered_errors
        })

        logger.info(f"Orchestration completed in {total_time:.1f}ms. Status: {plan.status}")
        return OrchestrationResult(
            plan=plan,
            results=results,
            response_text=response_text,
            total_time_ms=round(total_time, 2),
            recovered_errors=recovered_errors
        )


# Global Orchestrator singleton
orchestrator = Orchestrator()
