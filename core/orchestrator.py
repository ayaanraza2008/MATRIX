"""MATRIX Central Multi-Agent Orchestrator.
Coordinates the execution pipeline:
OBSERVE -> UNDERSTAND -> PLAN -> AUTHORIZE -> EXECUTE -> VERIFY -> RECOVER -> REPORT
"""
from typing import Dict, Any, List
import time
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
    def __init__(self, plan: ExecutionPlan, results: List[AgentResult], response_text: str, total_time_ms: float):
        self.plan = plan
        self.results = results
        self.response_text = response_text
        self.total_time_ms = total_time_ms


class Orchestrator:
    """Central engine delegating and verifying multi-agent tasks."""

    async def execute_request(self, prompt: str) -> OrchestrationResult:
        start_time = time.perf_counter()

        # 1. UNDERSTAND: Intent Extraction
        intent = intent_engine.classify(prompt)
        logger.info(f"Intent classified: {intent.intent_type.value} -> target agent: {intent.target_agent}")

        # 2. PLAN: Formulate multi-step ExecutionPlan
        plan = reasoning_engine.create_plan(intent)

        # 3. AUTHORIZE: Policy Gate Check
        if plan.requires_human_approval:
            logger.warning(f"Plan '{plan.title}' blocked: Requires human authorization (Risk Level {plan.max_risk_level})")
            return OrchestrationResult(
                plan=plan,
                results=[],
                response_text=(
                    f"Action requires explicit authorization (Risk Level {plan.max_risk_level}). "
                    f"Please confirm execution of '{plan.title}'."
                ),
                total_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

        # 4. EXECUTE & VERIFY
        results: List[AgentResult] = []
        plan.status = "RUNNING"

        for step in plan.steps:
            plan.mark_step_running(step.step_id)
            res = await task_router.dispatch(
                agent_name=step.agent_name,
                action=step.tool_name,
                parameters=step.arguments
            )
            results.append(res)

            if res.success:
                plan.mark_step_completed(step.step_id, result=res.data)
            else:
                plan.mark_step_failed(step.step_id, error=res.error or "Action verification failed")
                # Error recovery: log and break or retry
                logger.error(f"Step {step.step_id} ({step.title}) failed: {res.error}")
                break

        if plan.status != "FAILED":
            plan.status = "COMPLETED"

        # 5. REPORT: Synthesize unified response
        response_text = response_generator.format_agent_response(results, prompt)
        total_time = (time.perf_counter() - start_time) * 1000

        logger.info(f"Orchestration completed in {total_time:.1f}ms. Status: {plan.status}")
        return OrchestrationResult(
            plan=plan,
            results=results,
            response_text=response_text,
            total_time_ms=round(total_time, 2)
        )


# Global Orchestrator singleton
orchestrator = Orchestrator()
