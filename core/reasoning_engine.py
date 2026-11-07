"""MATRIX Reasoning Engine.
Decomposes user intents into structured execution plans, checks prerequisites,
evaluates risk levels (0-4), and assigns verification hooks.
"""
from typing import List, Dict, Any
from core.intent_engine import ParsedIntent, IntentType
from core.planner import ExecutionPlan, PlanStep
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("core.reasoning")


class ReasoningEngine:
    """Decomposes intent into actionable, verified multi-step execution plans."""

    def create_plan(self, intent: ParsedIntent) -> ExecutionPlan:
        """Formulate a step-by-step ExecutionPlan from a classified user intent."""
        steps: List[PlanStep] = []
        requires_approval = False
        max_risk = intent.required_autonomy_level

        if intent.intent_type == IntentType.COMMAND:
            steps.append(PlanStep(
                step_id=1,
                title=f"Execute PC Command: {intent.action}",
                agent_name="computer",
                tool_name="pc_execute",
                arguments={"action": intent.action, "raw_prompt": intent.raw_prompt, "entities": intent.entities},
                risk_level=intent.required_autonomy_level,
                verification_hook="verify_pc_action"
            ))

        elif intent.intent_type == IntentType.RESEARCH:
            steps.append(PlanStep(
                step_id=1,
                title="Conduct Multi-Source Web Research",
                agent_name="research",
                tool_name="web_research",
                arguments={"query": intent.parameters.get("query", intent.raw_prompt)},
                risk_level=1,
                verification_hook="verify_sources_found"
            ))
            steps.append(PlanStep(
                step_id=2,
                title="Synthesize Citations & Findings",
                agent_name="research",
                tool_name="synthesize_report",
                arguments={},
                risk_level=0,
                verification_hook="verify_markdown_generated"
            ))

        elif intent.intent_type == IntentType.CODING:
            steps.append(PlanStep(
                step_id=1,
                title="Inspect Codebase Workspace",
                agent_name="coding",
                tool_name="inspect_workspace",
                arguments={"query": intent.raw_prompt, "entities": intent.entities},
                risk_level=1,
                verification_hook="verify_files_found"
            ))
            steps.append(PlanStep(
                step_id=2,
                title="Execute Coding Task or Test Runner",
                agent_name="coding",
                tool_name="run_tests_or_edit",
                arguments={"instruction": intent.raw_prompt},
                risk_level=2,
                verification_hook="verify_test_results"
            ))

        elif intent.intent_type == IntentType.FILES:
            steps.append(PlanStep(
                step_id=1,
                title="Scan Protected File Directory (D:\\matrix_data)",
                agent_name="files",
                tool_name="scan_files",
                arguments={"entities": intent.entities, "query": intent.raw_prompt},
                risk_level=1,
                verification_hook="verify_file_read"
            ))

        elif intent.intent_type == IntentType.SYSTEM:
            steps.append(PlanStep(
                step_id=1,
                title="Poll Hardware Telemetry & Health",
                agent_name="system",
                tool_name="poll_telemetry",
                arguments={},
                risk_level=0,
                verification_hook="verify_telemetry_valid"
            ))

        elif intent.intent_type == IntentType.REPO_INTEL:
            steps.append(PlanStep(
                step_id=1,
                title="Query Starred Repositories Inventory",
                agent_name="repo_intel",
                tool_name="query_inventory",
                arguments={"query": intent.raw_prompt},
                risk_level=1,
                verification_hook="verify_repos_matched"
            ))

        else:
            # Direct conversational or answer step
            steps.append(PlanStep(
                step_id=1,
                title="Generate Core Model Response",
                agent_name="core",
                tool_name="generate_answer",
                arguments={"prompt": intent.raw_prompt},
                risk_level=0,
                verification_hook="verify_response_generated"
            ))

        # Check approval gate: Any action >= security_level requires user authorization
        if max_risk >= settings.security_level and settings.require_approval_high_risk:
            requires_approval = True

        plan = ExecutionPlan(
            title=f"Plan: {intent.intent_type.value.upper()} ({intent.action})",
            goal=intent.raw_prompt,
            steps=steps,
            max_risk_level=max_risk,
            requires_human_approval=requires_approval
        )

        logger.info(f"Formulated ExecutionPlan '{plan.title}' with {len(steps)} steps (Max Risk: {max_risk})")
        return plan


# Global Reasoning Engine singleton
reasoning_engine = ReasoningEngine()
