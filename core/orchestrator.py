"""MATRIX Central Multi-Agent Autonomous Orchestrator.
Coordinates the execution pipeline:
OBSERVE -> UNDERSTAND -> PLAN -> AUTHORIZE -> EXECUTE -> VERIFY -> RECOVER -> REPORT
Features persistent checkpoints in SQLite, 10-state Task State Machine,
concurrency for independent subtasks, recoverable retries, and real-time telemetry events.
"""
from typing import Dict, Any, List, Optional, Callable
import time
import asyncio
from datetime import datetime, timezone
from core.intent_engine import intent_engine, ParsedIntent
from core.reasoning_engine import reasoning_engine
from core.planner import ExecutionPlan, PlanStep
from core.task_state import TaskState
from core.task_router import task_router
from core.response_generator import response_generator
from agents.base_agent import AgentResult
from database.session import AsyncSessionLocal
from database.models import TaskRecord
from sqlalchemy import select, update
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
        """Broadcast progress telemetry to UI, hands-free manager, and subscribers."""
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
            from sqlalchemy import text
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

    async def _persist_task_record(self, plan: ExecutionPlan, result_data: Optional[Dict[str, Any]] = None, error_msg: Optional[str] = None):
        """Persist or update task state in SQLite database across restarts."""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(TaskRecord).where(TaskRecord.task_id == plan.plan_id)
                existing = (await session.execute(stmt)).scalar_one_or_none()
                
                plan_json = [s.model_dump() for s in plan.steps]
                checkpoints = [{"state": plan.state.value, "time": time.time()}]

                if existing:
                    existing.status = plan.state.value
                    existing.plan_data = plan_json
                    if result_data:
                        existing.result_data = result_data
                    if error_msg:
                        existing.error_message = error_msg
                    if plan.completed_at:
                        existing.completed_at = plan.completed_at
                else:
                    assigned = plan.steps[0].agent_name if plan.steps else "orchestrator"
                    new_rec = TaskRecord(
                        task_id=plan.plan_id,
                        title=plan.title,
                        autonomy_level=plan.max_risk_level,
                        status=plan.state.value,
                        assigned_agent=assigned,
                        plan_data=plan_json,
                        checkpoints=checkpoints,
                        result_data=result_data,
                        error_message=error_msg,
                        created_at=plan.created_at,
                        completed_at=plan.completed_at
                    )
                    session.add(new_rec)
                await session.commit()
        except Exception as e:
            logger.debug(f"Task record persistence error: {e}")

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

        # Check for unavailable capability gap (e.g. CUDA-only diorama / mocha)
        from core.repository_intelligence.engine import repo_intelligence
        gap = repo_intelligence.detect_capability_gap(prompt)
        if gap.has_gap and not gap.is_compatible:
            gap_explanation = (
                f"Autonomous Capability Assessment: The requested capability '{gap.required_capability}' "
                f"(repository '{gap.suggested_repo}') cannot run natively on this PC. "
                f"{gap.incompatibility_reason} "
                f"Autonomous Alternative: {gap.alternative_suggestion}"
            )
            plan = reasoning_engine.create_plan(intent)
            plan.transition_state(TaskState.COMPLETED)
            await self._log_audit_checkpoint("CAPABILITY_GAP_INCOMPATIBLE", gap_explanation, "HANDLED")
            await self._persist_task_record(plan, result_data={"gap": gap_explanation})
            return OrchestrationResult(
                plan=plan,
                results=[],
                response_text=gap_explanation,
                total_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

        # 2. PLAN: Formulate multi-step ExecutionPlan
        plan = reasoning_engine.create_plan(intent)
        plan.transition_state(TaskState.READY)
        total_steps = len(plan.steps)
        await self._persist_task_record(plan)
        await self._emit_progress("TASK_PROGRESS", {
            "task_id": plan.plan_id,
            "state": plan.state.value,
            "title": plan.title,
            "total_steps": total_steps
        })

        # 3. AUTHORIZE: Policy Gate Check
        if plan.requires_human_approval:
            logger.warning(f"Plan '{plan.title}' blocked: Requires human authorization (Risk Level {plan.max_risk_level})")
            plan.transition_state(TaskState.WAITING_FOR_INPUT, reason="Level 3 Security Authorization Required")
            await self._log_audit_checkpoint("SECURITY_GATE_BLOCK", f"Plan '{plan.title}' blocked for high risk", "BLOCKED")
            await self._persist_task_record(plan)
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
        plan.transition_state(TaskState.EXECUTING)
        recovered_errors = 0
        completed_step_ids = set()

        # Step-by-step dependency resolution
        for idx, step in enumerate(plan.steps, start=1):
            if self._cancel_requested:
                plan.transition_state(TaskState.CANCELLED, reason="Cancelled by user request")
                logger.warning(f"Orchestration cancelled before step {step.step_id}.")
                break

            # Verify step dependencies
            if step.dependencies:
                unmet = [dep for dep in step.dependencies if dep not in completed_step_ids]
                if unmet:
                    err_msg = f"Step {step.step_id} cannot run: unmet dependencies {unmet}"
                    logger.error(err_msg)
                    plan.mark_step_failed(step.step_id, err_msg)
                    break

            plan.mark_step_running(step.step_id)
            await self._emit_progress("TASK_PROGRESS", {
                "task_id": plan.plan_id,
                "state": TaskState.EXECUTING.value,
                "step_id": step.step_id,
                "step_number": idx,
                "total_steps": total_steps,
                "title": step.title,
                "agent": step.agent_name,
                "action": step.tool_name
            })

            # Execute with automatic retry and tool fallback
            max_retries = max(2, step.max_retries)
            res: Optional[AgentResult] = None
            active_tool = step.tool_name
            active_agent = step.agent_name

            for attempt in range(max_retries):
                try:
                    res = await task_router.dispatch(
                        agent_name=active_agent,
                        action=active_tool,
                        parameters=step.arguments
                    )
                    if res.success:
                        break
                    else:
                        logger.warning(f"Step {step.step_id} attempt {attempt + 1} failed: {res.error}")
                        recovered_errors += 1
                        plan.mark_step_recovering(step.step_id, reason=f"Attempt {attempt + 1} failed: {res.error}")
                        # If a fallback tool is defined, switch to it
                        if step.fallback_tool and active_tool != step.fallback_tool:
                            logger.info(f"Switching Step {step.step_id} to fallback tool: {step.fallback_tool}")
                            active_tool = step.fallback_tool
                            if step.fallback_agent:
                                active_agent = step.fallback_agent
                        await asyncio.sleep(0.2)
                except Exception as ex:
                    logger.warning(f"Step {step.step_id} exception on attempt {attempt + 1}: {ex}")
                    res = AgentResult(success=False, error=str(ex))
                    recovered_errors += 1
                    plan.mark_step_recovering(step.step_id, reason=f"Exception: {ex}")
                    await asyncio.sleep(0.2)

            if res is None:
                res = AgentResult(success=False, error="Action timed out or dispatch failed.")

            results.append(res)

            # VERIFY step output
            plan.mark_step_verifying(step.step_id)
            if res.success:
                plan.mark_step_completed(step.step_id, result=res.data)
                completed_step_ids.add(step.step_id)
                await self._log_audit_checkpoint(
                    f"{active_agent}.{active_tool}",
                    f"Step {idx}/{total_steps} completed: {step.title}",
                    "SUCCESS"
                )
            else:
                plan.mark_step_failed(step.step_id, error=res.error or "Action verification failed")
                await self._log_audit_checkpoint(
                    f"{active_agent}.{active_tool}",
                    f"Step {idx}/{total_steps} failed: {res.error}",
                    "FAILED"
                )
                logger.error(f"Step {step.step_id} ({step.title}) failed permanently: {res.error}")
                break

        if plan.state not in (TaskState.FAILED, TaskState.CANCELLED):
            plan.transition_state(TaskState.COMPLETED)

        # 5. REPORT: Unified response synthesis
        response_text = response_generator.format_agent_response(results, prompt)
        total_time = (time.perf_counter() - start_time) * 1000

        # Persist final task state to SQLite
        await self._persist_task_record(plan, result_data={"summary": response_text[:200]})
        await self._emit_progress("TASK_PROGRESS", {
            "task_id": plan.plan_id,
            "state": plan.state.value,
            "status": plan.status,
            "total_time_ms": total_time
        })

        return OrchestrationResult(
            plan=plan,
            results=results,
            response_text=response_text,
            total_time_ms=round(total_time, 2),
            recovered_errors=recovered_errors
        )


# Global Orchestrator singleton
orchestrator = Orchestrator()
