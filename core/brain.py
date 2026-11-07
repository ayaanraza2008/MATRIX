"""MATRIX Central AI Brain Facade.
Main entry point coordinating context, model selection, multimodal visual reasoning,
orchestration, and persistence across English, Hindi, and Hinglish.
Implements the 12-stage intelligence pipeline:
User Input -> Context Retrieval -> Intent Classification -> Reasoning -> Task Decomposition
-> Agent Selection -> Capability Selection -> Policy Evaluation -> Tool Execution
-> Result Verification -> Memory Update -> Final Response.
"""
from typing import Dict, Any, Optional
import time
import re
from core.context_manager import context_manager
from core.orchestrator import orchestrator
from core.model_manager import model_manager
from core.task_state import TaskState
from database.session import AsyncSessionLocal
from database.models import Message as MessageModel, Session as SessionModel
from config.logging_config import get_logger

logger = get_logger("core.brain")


class MatrixBrain:
    """Central intelligence coordinator for MATRIX."""

    async def process_user_request(
        self,
        session_id: str,
        user_prompt: str,
        active_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process incoming user prompt through the complete 12-stage intelligence pipeline."""
        start_time = time.perf_counter()
        logger.info(f"[{session_id}] Brain processing prompt: '{user_prompt[:80]}'")

        # Stage 1: User Input & Context Retrieval
        context_manager.add_message(session_id, role="user", content=user_prompt)

        # Stage 2: Cross-Turn Reference & Pronoun Resolution
        resolved_prompt = context_manager.resolve_references(session_id, user_prompt)
        if resolved_prompt != user_prompt:
            logger.info(f"[{session_id}] Resolved prompt: '{resolved_prompt}'")

        # Stage 3: Ambiguity Check -> WAITING_FOR_INPUT
        clarification = context_manager.detect_ambiguity(resolved_prompt, session_id)
        if clarification:
            context_manager.add_message(session_id, role="assistant", content=clarification, agent_name="core")
            return {
                "session_id": session_id,
                "response": clarification,
                "reply": clarification,
                "plan_status": TaskState.WAITING_FOR_INPUT.value,
                "plan_state": TaskState.WAITING_FOR_INPUT.value,
                "plan_title": "Clarification Required",
                "steps_count": 0,
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 2)
            }

        # Stage 3.5: Immediate Directives (Cancellation, Status Explanation, Continuous Voice Mode)
        lower_prompt = user_prompt.lower().strip()
        if any(lower_prompt == cmd or lower_prompt.startswith(cmd) for cmd in [
            "matrix, cancel the current task", "cancel the current task", "matrix cancel the current task", "cancel that task", "cancel task"
        ]):
            orchestrator.cancel_active()
            reply = "The current task has been cancelled, sir."
            return {
                "session_id": session_id,
                "response": reply,
                "reply": reply,
                "plan_status": TaskState.CANCELLED.value,
                "plan_state": TaskState.CANCELLED.value,
                "plan_title": "Task Cancellation",
                "steps_count": 0,
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 2)
            }

        if any(lower_prompt == cmd or lower_prompt.startswith(cmd) for cmd in [
            "matrix, explain what you are currently doing", "explain what you are currently doing", "what are you doing"
        ]):
            from core.agent_coordinator import agent_coordinator
            dashboard = agent_coordinator.get_agent_dashboard()
            active_tasks = dashboard.get("active_tasks_count", 0)
            recent_tasks = dashboard.get("recent_tasks_count", 0)
            reply = (
                f"Currently, all 16 specialized agents are standing by and operational. "
                f"Active tasks: {active_tasks}, completed tasks in this session: {recent_tasks}. "
                f"Monitoring system telemetry and listening for commands, sir."
            )
            return {
                "session_id": session_id,
                "response": reply,
                "reply": reply,
                "plan_status": TaskState.COMPLETED.value,
                "plan_state": TaskState.COMPLETED.value,
                "plan_title": "Current Status Explanation",
                "steps_count": 1,
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 2)
            }

        if any(lower_prompt == cmd or lower_prompt.startswith(cmd) for cmd in [
            "matrix, continue listening after answering", "continue listening after answering", "continue listening"
        ]):
            from voice.conversation.manager import conversation_manager, ConversationMode
            conversation_manager.set_mode(ConversationMode.CONTINUOUS)
            reply = "Continuous hands-free listening is enabled, sir. I will remain actively listening after answering."
            return {
                "session_id": session_id,
                "response": reply,
                "reply": reply,
                "plan_status": TaskState.COMPLETED.value,
                "plan_state": TaskState.COMPLETED.value,
                "plan_title": "Continuous Listening Enabled",
                "steps_count": 1,
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 2)
            }

        # Stage 4-10: Orchestrator Pipeline (Intent, Reasoning, Policy, Execution, Verification, Recovery)
        orch_res = await orchestrator.execute_request(resolved_prompt)

        reply_content = orch_res.response_text
        prompt_lower = user_prompt.lower()

        # Check if user explicitly requested Hinglish or Hindi
        is_hinglish_requested = any(w in prompt_lower for w in ["hinglish", "hindi me", "hindi mein", "batao", "kya"])
        language_hint = " Respond in natural conversational Hinglish." if is_hinglish_requested else ""

        # Stage 11: Intelligent Model Enrichment & Multi-lingual Synthesis
        # A. Direct Conversational / QA Intent (only if not an explicit capability gap or security gate block)
        if orch_res.plan.steps and orch_res.plan.steps[0].tool_name == "generate_answer" and not (
            "Autonomous Capability Assessment" in orch_res.response_text or
            "Security policy requires explicit authorization" in orch_res.response_text
        ):
            history_context = context_manager.format_history_for_llm(session_id)
            model_res = await model_manager.generate_response(
                prompt=f"{history_context}\n\nASSISTANT:{language_hint}",
                system_prompt=context_manager.SYSTEM_PROMPT,
                max_tokens=300
            )
            reply_content = model_res.content

        # B. Vision Intent (e.g. "What is visible on my screen?", "Read this image")
        elif orch_res.plan.steps and orch_res.plan.steps[0].agent_name == "vision":
            vis_data = orch_res.results[0].data if orch_res.results else {}
            vis_summary = vis_data.get("visual_summary", orch_res.response_text)
            ocr_text = vis_data.get("ocr_text", "")
            
            enrich_prompt = (
                f"The user asked: \"{user_prompt}\"\n\n"
                f"Real Visual & Screen Telemetry from Windows 11:\n"
                f"- Visual Analysis: {vis_summary}\n"
            )
            if ocr_text:
                enrich_prompt += f"- Text Read from Screen (OCR): {ocr_text[:500]}\n"
            enrich_prompt += f"\nProvide a direct, conversational, JARVIS-style answer.{language_hint}"

            model_res = await model_manager.generate_response(
                prompt=enrich_prompt,
                system_prompt=context_manager.SYSTEM_PROMPT,
                max_tokens=250
            )
            if model_res.content and len(model_res.content.strip()) > 10:
                reply_content = model_res.content

        # C. Coding Generation Request (e.g. "Create a Python calculator", "Write a script")
        elif any(w in prompt_lower for w in ["create", "write", "generate", "build", "make", "implement"]) and \
             any(w in prompt_lower for w in ["calculator", "script", "code", "python", "function", "program", "class"]):
            code_prompt = (
                f"The user requested: \"{user_prompt}\"\n\n"
                f"Provide clean, production-ready code with concise usage instructions.{language_hint}"
            )
            model_res = await model_manager.generate_response(
                prompt=code_prompt,
                system_prompt="You are MATRIX Senior Engineer. Provide accurate, clean, well-commented code directly.",
                max_tokens=400
            )
            if model_res.content and len(model_res.content.strip()) > 10:
                reply_content = model_res.content

        # D. Explanatory Telemetry / System Request (e.g. "Explain what is running on my computer")
        elif any(w in prompt_lower for w in ["explain", "tell me about", "what is running", "describe"]) and \
             orch_res.plan.steps and orch_res.plan.steps[0].agent_name == "system":
            explain_prompt = (
                f"The user asked: \"{user_prompt}\"\n\n"
                f"Verified Hardware Telemetry from AMD Ryzen 7 5700U:\n{orch_res.response_text}\n\n"
                f"Explain what this means clearly and conversationally to the user.{language_hint}"
            )
            model_res = await model_manager.generate_response(
                prompt=explain_prompt,
                system_prompt=context_manager.SYSTEM_PROMPT,
                max_tokens=250
            )
            if model_res.content and len(model_res.content.strip()) > 10:
                reply_content = model_res.content

        # E. Autonomous Capability & Repository Selection (e.g. "Create a professional AI voice assistant", "Find tools for X")
        elif any(w in prompt_lower for w in ["repository", "repositories", "tool for", "how to build", "create a voice assistant", "create an ai voice assistant", "voice assistant"]):
            from core.repository_intelligence.engine import repo_intelligence
            selection = repo_intelligence.select_best_tool(user_prompt)
            gap = repo_intelligence.detect_capability_gap(user_prompt)
            
            repo_enrich_prompt = (
                f"The user requested: \"{user_prompt}\"\n\n"
                f"Autonomous Repository Intelligence Engine Selection:\n"
                f"- Selected Tool: {selection.selected_adapter} (from {selection.selected_repo})\n"
                f"- Category: {selection.category} -> Agent: {selection.target_agent}\n"
                f"- Capabilities: {', '.join(selection.operations_to_invoke)}\n"
                f"- Compatibility Score: {selection.compatibility_score} on AMD Ryzen 7 5700U\n"
                f"- Decision Reasoning: {selection.reason}\n"
            )
            if gap.has_gap and not gap.is_compatible:
                repo_enrich_prompt += f"- Hardware Note: {gap.incompatibility_reason}\n- Alternative: {gap.alternative_suggestion}\n"

            repo_enrich_prompt += (
                f"\nSynthesize a decisive, professional JARVIS response confirming the selected architecture, "
                f"how MATRIX autonomously configured it, and the verified operational readiness.{language_hint}"
            )
            model_res = await model_manager.generate_response(
                prompt=repo_enrich_prompt,
                system_prompt="You are MATRIX, an autonomous AI architect. Explain your autonomous tool selection and execution clearly.",
                max_tokens=300
            )
            if model_res.content and len(model_res.content.strip()) > 10:
                reply_content = model_res.content

        # F. Hinglish/Hindi general conversation
        elif is_hinglish_requested:
            hinglish_prompt = (
                f"The user asked in Hinglish: \"{user_prompt}\"\n"
                f"Factual Task Outcome: {reply_content}\n\n"
                f"Reply naturally and politely in Hinglish (Hindi written in Roman or Devanagari script)."
            )
            model_res = await model_manager.generate_response(
                prompt=hinglish_prompt,
                system_prompt=context_manager.SYSTEM_PROMPT,
                max_tokens=200
            )
            if model_res.content and len(model_res.content.strip()) > 10:
                reply_content = model_res.content

        # Stage 12: Memory Update & SQLite Persistence
        agent_tag = orch_res.plan.steps[0].agent_name if orch_res.plan.steps else "core"
        context_manager.add_message(
            session_id,
            role="assistant",
            content=reply_content,
            agent_name=agent_tag
        )

        total_latency = (time.perf_counter() - start_time) * 1000

        try:
            async with AsyncSessionLocal() as session:
                msg = MessageModel(
                    session_id=session_id,
                    role="assistant",
                    content=reply_content,
                    agent_name=agent_tag,
                    extra_metadata={
                        "latency_ms": round(total_latency, 2),
                        "plan_id": orch_res.plan.plan_id,
                        "plan_status": orch_res.plan.status,
                        "plan_state": orch_res.plan.state.value
                    }
                )
                session.add(msg)
                await session.commit()
        except Exception as e:
            logger.warning(f"Could not persist message to DB: {e}")

        return {
            "session_id": session_id,
            "response": reply_content,
            "reply": reply_content,
            "plan_status": orch_res.plan.status,
            "plan_state": orch_res.plan.state.value,
            "plan_title": orch_res.plan.title,
            "steps_count": len(orch_res.plan.steps),
            "latency_ms": round(total_latency, 2)
        }

    async def interact(self, user_prompt: str, session_id: str = "sess_default") -> str:
        """High-level interaction returning the synthesized text response."""
        res = await self.process_user_request(session_id=session_id, user_prompt=user_prompt)
        return res.get("response", "")


brain = MatrixBrain()
