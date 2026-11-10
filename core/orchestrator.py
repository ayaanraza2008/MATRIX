"""MATRIX Central Multi-Agent Autonomous Orchestrator.
Coordinates the execution pipeline:
OBSERVE -> UNDERSTAND -> PLAN -> AUTHORIZE -> EXECUTE -> VERIFY -> RECOVER -> REPORT
Features persistent checkpoints in SQLite, 10-state Task State Machine,
concurrency for independent subtasks, recoverable retries, and real-time telemetry events.
"""
from typing import Dict, Any, List, Optional, Callable, Tuple
import time
import asyncio
from datetime import datetime, timezone
from core.intent_engine import intent_engine
from core.reasoning_engine import reasoning_engine
from core.planner import ExecutionPlan, PlanStep
from core.task_state import TaskState
from core.task_router import task_router
from core.response_generator import response_generator
from agents.base_agent import AgentResult
from database.session import AsyncSessionLocal
from database.models import TaskRecord
from sqlalchemy import select
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

    @property
    def success(self) -> bool:
        return self.plan is not None and self.plan.state == TaskState.COMPLETED


class Orchestrator:
    """Autonomous engine for planning, policy gating, delegating, verifying, and recovering multi-agent tasks."""

    NON_IDEMPOTENT_TOOLS = {
        "delete_file", "delete_folder", "remove_directory", "send_email",
        "send_message", "schedule_call", "make_call", "synthesize_speech",
        "create_workflow", "pair", "draft_email"
    }

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

    def _verify_step_outcome(self, step: PlanStep, res: AgentResult) -> Tuple[bool, Optional[str]]:
        """Verify that step execution achieved its goal on disk, in memory, or in OS state with independent evidence."""
        from pathlib import Path
        import psutil

        if not res.success:
            return False, res.error or "Step reported execution failure."

        hook = step.verification_hook or ""
        data = res.data or {}

        try:
            # 1. Verification of Application Launch (e.g. Notepad, Calc, Browser)
            if hook in ("verify_app_opened", "verify_process_running") or "launch" in step.tool_name.lower():
                app_target = str(data.get("application") or data.get("executable") or step.arguments.get("app") or step.arguments.get("action") or "").lower()
                stem = Path(app_target).stem.replace("start ", "").strip()
                if stem:
                    is_running = any(stem in p.info['name'].lower() for p in psutil.process_iter(['name', 'pid']) if p.info and p.info.get('name'))
                    if not is_running:
                        return False, f"Process '{stem}' confirmed NOT running in Windows process table."
                return True, None

            # 2. Verification of Folder Creation
            elif hook in ("verify_folder_created", "verify_directory_exists") or "create_folder" in step.tool_name.lower():
                fpath = data.get("folder_path") or data.get("directory") or step.arguments.get("target_dir")
                if fpath:
                    p = Path(fpath)
                    if not (p.exists() and p.is_dir()):
                        return False, f"Directory '{fpath}' does not exist on disk after creation."
                return True, None

            # 3. Verification of File Creation & Report Saving
            elif hook in ("verify_report_saved", "verify_file_created") or "create_file" in step.tool_name.lower():
                fpath = data.get("filepath") or step.arguments.get("filepath")
                if fpath:
                    p = Path(fpath)
                    if not (p.exists() and p.is_file()):
                        return False, f"File '{fpath}' does not exist on disk after creation."
                    if p.stat().st_size == 0 and "content" in step.arguments and len(step.arguments["content"]) > 0:
                        return False, f"File '{fpath}' was created empty (0 bytes) despite non-empty content."
                return True, None

            # 4. Verification of File Read
            elif hook in ("verify_file_read", "verify_read_file") or "read" in step.tool_name.lower():
                fpath = data.get("filepath") or step.arguments.get("filepath")
                if fpath:
                    p = Path(fpath)
                    if not p.exists():
                        return False, f"File '{fpath}' does not exist on disk to read."
                text = data.get("text")
                if text is None:
                    return False, "File read produced no content or text representation."
                return True, None

            # 5. Independent Mathematical Calculation Verification
            elif hook in ("verify_calculation", "verify_math") or "calc" in step.tool_name.lower():
                import ast
                import operator
                import re
                expr = str(data.get("expression") or step.arguments.get("expression") or step.arguments.get("query") or "")
                clean_expr = re.sub(r'^(?:calculate|compute|solve|what is|eval)\s+', '', expr, flags=re.IGNORECASE).strip().rstrip('?=. ')
                operators = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos}
                def eval_n(node):
                    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)): return node.value
                    elif isinstance(node, ast.BinOp): return operators[type(node.op)](eval_n(node.left), eval_n(node.right))
                    elif isinstance(node, ast.UnaryOp): return operators[type(node.op)](eval_n(node.operand))
                    raise ValueError("invalid math node")
                if clean_expr:
                    tree = ast.parse(clean_expr, mode='eval')
                    expected = eval_n(tree.body)
                    actual = data.get("result")
                    if actual is None or abs(float(actual) - float(expected)) > 1e-6:
                        return False, f"Math calculation mismatch: Tool reported {actual}, independent evaluation yielded {expected}."
                return True, None

            # 6. Verification of Real OS Hardware Telemetry
            elif hook in ("verify_telemetry_valid", "verify_system_diagnosed") or "telemetry" in step.tool_name.lower():
                if not data or ("cpu" not in data and "hardware" not in data and "telemetry" not in data and "cpu_percent" not in data):
                    return False, "Telemetry data empty or malformed."
                cpu = data.get("cpu_percent") or (data.get("cpu", {}).get("percent") if isinstance(data.get("cpu"), dict) else None)
                if cpu is not None and (cpu < 0.0 or cpu > 100.0):
                    return False, f"Telemetry CPU value {cpu}% is outside physical bounds [0, 100]."
                return True, None

            # 7. Verification of Browser / Web Action
            elif hook in ("verify_sources_found", "verify_web_navigated") or "browser" in step.agent_name.lower():
                if "error" in data:
                    return False, str(data["error"])
                return True, None

            # 8. Simulated / Mock Output Detection
            if isinstance(data, dict):
                if data.get("simulated") is True or data.get("mocked") is True:
                    return False, "Simulated or mocked tool execution detected where real execution was required."

        except Exception as e:
            return False, f"Verification hook exception: {e}"

        return True, None

    async def recover_interrupted_tasks(self) -> List[Dict[str, Any]]:
        """Inspect and recover or safely finalize interrupted workflows from SQLite."""
        recovered = []
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(TaskRecord).where(
                    TaskRecord.status.in_([TaskState.EXECUTING.value, TaskState.RECOVERING.value])
                )
                tasks = (await session.execute(stmt)).scalars().all()
                for t in tasks:
                    t.status = TaskState.INTERRUPTED.value
                    t.error_message = "Task execution was interrupted by process restart; state preserved safely."
                    recovered.append({"task_id": t.task_id, "title": t.title, "status": "INTERRUPTED_RECOVERED"})
                await session.commit()
        except Exception as e:
            logger.warning(f"Error during interrupted task recovery: {e}")
        return recovered

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

    async def execute_request(
        self,
        prompt: Optional[str] = None,
        session_id: Optional[str] = None,
        user_prompt: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> OrchestrationResult:
        import uuid
        start_time = time.perf_counter()
        self._cancel_requested = False
        target_prompt = prompt or user_prompt or ""
        req_id = (request_id or "").strip() or f"req_{uuid.uuid4().hex[:12]}"

        # 1. OBSERVE & UNDERSTAND: Intent Extraction
        intent = intent_engine.classify(target_prompt)
        logger.info(f"Intent classified: {intent.intent_type.value} -> target agent: {intent.target_agent}")
        await self._emit_progress("AGENT_SELECTED", {
            "agent": intent.target_agent,
            "intent": intent.intent_type.value
        })

        # Check for unavailable capability gap (e.g. CUDA-only diorama / mocha)
        from core.repository_intelligence.engine import repo_intelligence
        gap = repo_intelligence.detect_capability_gap(target_prompt)
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

            # If step has dependencies, propagate results from previous steps
            if step.dependencies:
                for dep_id in step.dependencies:
                    for prev_r in results:
                        if prev_r.success and isinstance(prev_r.data, dict):
                            step.arguments.setdefault("dependency_data", prev_r.data)
                            if "report_markdown" in prev_r.data and "content" in step.arguments:
                                step.arguments["content"] = prev_r.data["report_markdown"]

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

            # Non-idempotent actions must NOT be retried multiple times
            if step.tool_name in self.NON_IDEMPOTENT_TOOLS:
                max_retries = 1
            else:
                max_retries = max(1, step.max_retries)

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

            # Populate Phase 3 Contract Fields on AgentResult
            res.request_id = req_id
            res.task_id = plan.plan_id
            res.step_id = step.step_id
            res.tool_name = active_tool
            res.actual_result = res.data

            # VERIFY step output independently
            plan.mark_step_verifying(step.step_id)
            is_valid, verify_err = self._verify_step_outcome(step, res)
            if is_valid:
                res.execution_status = "SUCCESS"
                res.verification_status = "VERIFIED"
                res.verification["verified"] = True
                plan.mark_step_completed(step.step_id, result=res.data)
                completed_step_ids.add(step.step_id)
                await self._log_audit_checkpoint(
                    f"{active_agent}.{active_tool}",
                    f"Step {idx}/{total_steps} completed: {step.title}",
                    "SUCCESS"
                )
            else:
                res.success = False
                res.execution_status = "FAILED"
                res.verification_status = "FAILED"
                res.error = verify_err or res.error or "Action verification failed"
                res.error_details = res.error
                plan.mark_step_failed(step.step_id, error=res.error)
                await self._log_audit_checkpoint(
                    f"{active_agent}.{active_tool}",
                    f"Step {idx}/{total_steps} failed: {res.error}",
                    "FAILED"
                )
                logger.error(f"Step {step.step_id} ({step.title}) failed verification: {res.error}")
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
