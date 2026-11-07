"""MATRIX Central AI Brain Facade.
Main entry point coordinating context, model selection, reasoning, orchestration, and persistence.
"""
from typing import Dict, Any, Optional
import time
from core.context_manager import context_manager
from core.orchestrator import orchestrator
from core.model_manager import model_manager
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
        """Process incoming user prompt through the complete intelligence pipeline."""
        start_time = time.perf_counter()
        logger.info(f"[{session_id}] Brain processing prompt: '{user_prompt[:80]}'")

        # 1. Update Context Manager
        context_manager.add_message(session_id, role="user", content=user_prompt)

        # 2. Run Orchestrator Pipeline
        orch_res = await orchestrator.execute_request(user_prompt)

        reply_content = orch_res.response_text

        # 3. If direct conversational answer, allow model manager to enrich
        if orch_res.plan.steps and orch_res.plan.steps[0].tool_name == "generate_answer":
            model_res = await model_manager.generate_response(
                prompt=user_prompt,
                system_prompt=context_manager.SYSTEM_PROMPT
            )
            reply_content = model_res.content

        # 4. Update Context Manager with reply
        context_manager.add_message(
            session_id,
            role="assistant",
            content=reply_content,
            agent_name=orch_res.plan.steps[0].agent_name if orch_res.plan.steps else "core"
        )

        total_latency = (time.perf_counter() - start_time) * 1000

        # 5. Persist assistant reply in SQLite
        try:
            async with AsyncSessionLocal() as session:
                msg = MessageModel(
                    session_id=session_id,
                    role="assistant",
                    content=reply_content,
                    agent_name=orch_res.plan.steps[0].agent_name if orch_res.plan.steps else "core",
                    extra_metadata={
                        "latency_ms": round(total_latency, 2),
                        "plan_id": orch_res.plan.plan_id,
                        "plan_status": orch_res.plan.status
                    }
                )
                session.add(msg)
                await session.commit()
        except Exception as e:
            logger.warning(f"Could not persist message to DB: {e}")

        return {
            "session_id": session_id,
            "response": reply_content,
            "plan_status": orch_res.plan.status,
            "plan_title": orch_res.plan.title,
            "steps_count": len(orch_res.plan.steps),
            "latency_ms": round(total_latency, 2)
        }


# Global Matrix Brain singleton
brain = MatrixBrain()
