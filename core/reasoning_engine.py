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
            if intent.target_agent == "research":
                steps.append(PlanStep(
                    step_id=1,
                    title="Execute Deep Research Dossier",
                    agent_name="research",
                    tool_name="execute",
                    arguments={"query": intent.parameters.get("query", intent.raw_prompt)},
                    risk_level=1,
                    verification_hook="verify_sources_found"
                ))
            else:
                steps.append(PlanStep(
                    step_id=1,
                    title="Execute Web Search & Browser Extraction",
                    agent_name="browser",
                    tool_name="search_web",
                    arguments={"query": intent.parameters.get("query", intent.raw_prompt)},
                    risk_level=1,
                    verification_hook="verify_sources_found"
                ))

        elif intent.intent_type == IntentType.CODING:
            p_low = intent.raw_prompt.lower()
            if any(w in p_low for w in ["analyze", "inspect", "architecture", "ast"]) and any(ext in p_low for ext in [".py", "python file", "code"]):
                # Extract file path if provided
                import re
                matches = re.findall(r'[\w/\\.-]+\.py', intent.raw_prompt)
                target_file = matches[0] if matches else "core/brain.py"
                steps.append(PlanStep(
                    step_id=1,
                    title=f"Analyze Code Architecture: {target_file}",
                    agent_name="coding",
                    tool_name="inspect_code_architecture",
                    arguments={"file_path": target_file, "raw_prompt": intent.raw_prompt},
                    risk_level=1,
                    verification_hook="verify_ast_inspected"
                ))
            else:
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

        elif intent.intent_type == IntentType.MEMORY:
            p_low = intent.raw_prompt.lower()
            if any(w in p_low for w in ["save", "store", "remember", "favorite"]):
                steps.append(PlanStep(
                    step_id=1,
                    title="Store Preference in Long-Term Memory",
                    agent_name="memory",
                    tool_name="save_memory",
                    arguments={"query": intent.raw_prompt, "prompt": intent.raw_prompt},
                    risk_level=1,
                    verification_hook="verify_memory_saved"
                ))
            else:
                steps.append(PlanStep(
                    step_id=1,
                    title="Retrieve Context from Memory",
                    agent_name="memory",
                    tool_name="list_memory",
                    arguments={"query": intent.raw_prompt},
                    risk_level=1,
                    verification_hook="verify_memory_retrieved"
                ))

        elif intent.intent_type == IntentType.CREATIVE:
            steps.append(PlanStep(
                step_id=1,
                title="Generate Architecture Blueprint & Mermaid Diagram",
                agent_name="creative",
                tool_name="generate_mermaid",
                arguments={"prompt": intent.raw_prompt, "query": intent.raw_prompt},
                risk_level=1,
                verification_hook="verify_diagram_rendered"
            ))

        elif intent.intent_type == IntentType.VOICE:
            steps.append(PlanStep(
                step_id=1,
                title="Synthesize Speech via Neural TTS",
                agent_name="voice",
                tool_name="synthesize_speech",
                arguments={"text": intent.raw_prompt, "query": intent.raw_prompt},
                risk_level=0,
                verification_hook="verify_speech_synthesized"
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

        elif intent.intent_type == IntentType.VISION:
            steps.append(PlanStep(
                step_id=1,
                title="Inspect Screen & Read Display via OCR",
                agent_name="vision",
                tool_name="inspect_screen",
                arguments={"query": intent.raw_prompt},
                risk_level=1,
                verification_hook="verify_vision_inspected"
            ))

        elif intent.intent_type == IntentType.ANDROID:
            steps.append(PlanStep(
                step_id=1,
                title="Generate Android Companion Token & Device Status",
                agent_name="android",
                tool_name="pair",
                arguments={"action": "pair"},
                risk_level=1,
                verification_hook="verify_android_token"
            ))

        elif intent.intent_type == IntentType.DATA_ANALYSIS:
            steps.append(PlanStep(
                step_id=1,
                title="Analyze Tabular Dataset & Statistics",
                agent_name="data_analysis",
                tool_name="analyze_csv",
                arguments=intent.parameters,
                risk_level=1,
                verification_hook="verify_data_analyzed"
            ))

        elif intent.intent_type == IntentType.WORKFLOW:
            steps.append(PlanStep(
                step_id=1,
                title="Schedule Automated Workflow",
                agent_name="automation",
                tool_name="create_workflow",
                arguments={"title": intent.raw_prompt, "steps": []},
                risk_level=2,
                verification_hook="verify_workflow_scheduled"
            ))

        elif intent.intent_type == IntentType.SECURITY:
            steps.append(PlanStep(
                step_id=1,
                title="Inspect Security Policy & Payload",
                agent_name="security",
                tool_name="evaluate_payload",
                arguments={"command": intent.raw_prompt},
                risk_level=1,
                verification_hook="verify_security_audit"
            ))

        elif intent.intent_type == IntentType.QUERY:
            steps.append(PlanStep(
                step_id=1,
                title="Personal Assistant Response",
                agent_name="personal",
                tool_name="answer",
                arguments={"query": intent.raw_prompt},
                risk_level=0,
                verification_hook="verify_personal_response"
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

        # Check approval gate: Any action >= security_level or flagged by policy requires user authorization
        from core.autonomy_policy.policy import autonomy_policy, ActionCategory
        policy_check = autonomy_policy.evaluate(
            ActionCategory.DESTRUCTIVE_SYSTEM_COMMAND if max_risk >= 3 else ActionCategory.RUN_APPROVED_TOOL,
            details={"command": intent.raw_prompt, "prompt": intent.raw_prompt}
        )
        if policy_check.requires_user_confirmation or (max_risk >= settings.security_level and settings.require_approval_high_risk):
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
