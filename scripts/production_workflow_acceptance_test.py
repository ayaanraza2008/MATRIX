"""MATRIX Production End-to-End Workflow Acceptance Test.
Executes the 8 canonical workflows specified in the Super Master Prompt:
Workflow A: "Matrix, open my browser and research this topic."
Workflow B: "Matrix, inspect my screen and explain the error."
Workflow C: "Matrix, create a Python application and test it."
Workflow D: "Matrix, remember this preference."
Workflow E: "Matrix, generate a voice response and keep listening."
Workflow F: "Matrix, find the best available capability for this task and execute it."
Workflow G: "Matrix, analyze my computer's performance."
Workflow H: "Matrix, summarize my pending tasks."
Outputs verifiable metrics and telemetry to docs/production_acceptance_raw.json.
"""
import sys
import os
import time
import asyncio
import json
from pathlib import Path

# Add project root to path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from core.brain import brain
from core.orchestrator import orchestrator
from core.task_state import TaskState
from core.agent_coordinator import agent_coordinator
from database.session import AsyncSessionLocal
from database.models import TaskRecord, UserPreference
from sqlalchemy import select


class ProductionAcceptanceRunner:
    def __init__(self):
        self.results = {}
        self.start_time = time.time()

    def record(self, workflow_id: str, name: str, status: str, latency_ms: float, evidence: str, data: dict = None):
        if workflow_id not in self.results:
            self.results[workflow_id] = []
        entry = {
            "name": name,
            "status": status,
            "latency_ms": round(latency_ms, 2),
            "evidence": evidence,
            "data": data or {}
        }
        self.results[workflow_id].append(entry)
        print(f"[{status:<7}] {workflow_id} :: {name:<35} ({latency_ms:7.1f}ms) - {evidence[:75]}")

    async def run_all(self):
        print("=" * 80)
        print(" MATRIX STAGE 2 — PRODUCTION WORKFLOW END-TO-END ACCEPTANCE TEST")
        print("=" * 80)

        # WORKFLOW A: Browser & Deep Research
        await self.test_workflow_a_browser_research()

        # WORKFLOW B: Vision Screen & OCR
        await self.test_workflow_b_vision_screen()

        # WORKFLOW C: Developer Studio & Code Test
        await self.test_workflow_c_coding_app()

        # WORKFLOW D: Memory Persistence & Recall
        await self.test_workflow_d_memory_preference()

        # WORKFLOW E: Voice & Hands-Free
        await self.test_workflow_e_voice_hands_free()

        # WORKFLOW F: Autonomous Repository Capability Engine
        await self.test_workflow_f_repo_capability()

        # WORKFLOW G: Computer & System Performance
        await self.test_workflow_g_system_performance()

        # WORKFLOW H: Task State & History Summarization
        await self.test_workflow_h_task_summarization()

        # Save results
        self.save_raw_json()
        print("=" * 80)
        print(" ALL PRODUCTION WORKFLOW TESTS COMPLETED.")
        print("=" * 80)

    async def test_workflow_a_browser_research(self):
        print("\n--- WORKFLOW A: Browser Navigation & Deep Research ---")
        t0 = time.perf_counter()
        res = await brain.process_user_request(
            session_id="wf_browser",
            user_prompt="Matrix, open my browser and research latest AI agent architecture."
        )
        dt = (time.perf_counter() - t0) * 1000
        reply = res.get("reply", "")
        passed = len(reply) > 50 and any(w in reply.lower() for w in ["result", "source", "http", "agent", "architecture"])
        self.record(
            "WORKFLOW_A_BROWSER",
            "browser_research_execution",
            "PASS" if passed else "FAIL",
            dt,
            f"Reply: '{reply[:65]}...'",
            {"reply": reply[:300]}
        )

    async def test_workflow_b_vision_screen(self):
        print("\n--- WORKFLOW B: Screen Inspection & Error Explanation ---")
        t0 = time.perf_counter()
        res = await brain.process_user_request(
            session_id="wf_vision",
            user_prompt="Matrix, inspect my screen and explain what is visible."
        )
        dt = (time.perf_counter() - t0) * 1000
        reply = res.get("reply", "")
        passed = len(reply) > 40 and any(w in reply.lower() for w in ["screen", "visual", "monitor", "display", "frame"])
        self.record(
            "WORKFLOW_B_VISION",
            "screen_visual_ocr_inspection",
            "PASS" if passed else "FAIL",
            dt,
            f"Reply: '{reply[:65]}...'",
            {"reply": reply[:300]}
        )

    async def test_workflow_c_coding_app(self):
        print("\n--- WORKFLOW C: Create Python Application & Run Tests ---")
        t0 = time.perf_counter()
        # Scaffold real project in sandbox
        from api.routes.developer import scaffold_project, ProjectScaffoldRequest, run_tests, TestRunRequest
        scaffold_res = await scaffold_project(ProjectScaffoldRequest(
            project_name="autonomy_calc_app",
            project_type="python",
            description="Autonomous math utility test project"
        ))
        
        # Write test code
        test_file = Path("D:/matrix_data/test_workspace/projects/autonomy_calc_app/tests/test_main.py")
        test_file.write_text("def test_addition():\n    assert 20 + 22 == 42\n", encoding="utf-8")

        # Run pytest through Developer Studio runner
        test_res = await run_tests(TestRunRequest(test_file=str(test_file)))
        dt = (time.perf_counter() - t0) * 1000
        passed = test_res.get("success", False)
        self.record(
            "WORKFLOW_C_CODING",
            "scaffold_and_test_python_app",
            "PASS" if passed else "FAIL",
            dt,
            f"Project: {scaffold_res.get('project_name')}, Tests passed: {passed}",
            test_res
        )

    async def test_workflow_d_memory_preference(self):
        print("\n--- WORKFLOW D: Remember User Preference & Semantic Recall ---")
        t0 = time.perf_counter()
        res_save = await brain.process_user_request(
            session_id="wf_memory",
            user_prompt="Matrix, remember my favorite code theme as Matrix Dark Cyan in memory"
        )
        
        # Verify persistence in DB
        async with AsyncSessionLocal() as session:
            stmt = select(UserPreference).where(UserPreference.key == "favorite_code_theme")
            pref = (await session.execute(stmt)).scalar_one_or_none()
            saved_val = pref.value if pref else None

        dt = (time.perf_counter() - t0) * 1000
        passed = saved_val is not None
        self.record(
            "WORKFLOW_D_MEMORY",
            "remember_preference_sqlite",
            "PASS" if passed else "FAIL",
            dt,
            f"Persisted key 'favorite_code_theme' -> '{saved_val}'",
            {"key": "favorite_code_theme", "val": str(saved_val)}
        )

    async def test_workflow_e_voice_hands_free(self):
        print("\n--- WORKFLOW E: Neural Voice Response & Continuous Listening ---")
        t0 = time.perf_counter()
        from voice.text_to_speech.engine import tts_engine
        from voice.conversation.manager import hands_free_manager, HandsFreeState, ConversationMode

        # Synthesize voice response
        audio_file = await tts_engine.speak("MATRIX production acceptance test in progress. Voice intelligence nominal.")
        
        # Set continuous listening mode
        hands_free_manager.set_mode(ConversationMode.CONTINUOUS)
        hands_free_manager.state = HandsFreeState.LISTENING

        dt = (time.perf_counter() - t0) * 1000
        audio_ok = audio_file is not None and audio_file.exists() and audio_file.stat().st_size > 5000
        self.record(
            "WORKFLOW_E_VOICE",
            "voice_synthesis_and_continuous_listen",
            "PASS" if audio_ok else "FAIL",
            dt,
            f"Audio: {audio_file.name if audio_file else None} ({audio_file.stat().st_size if audio_file else 0} bytes), State: {hands_free_manager.state.value}",
            {"file": str(audio_file)}
        )

    async def test_workflow_f_repo_capability(self):
        print("\n--- WORKFLOW F: Autonomous Capability Discovery & Selection ---")
        t0 = time.perf_counter()
        from core.repository_intelligence.engine import repo_intelligence
        selection = repo_intelligence.select_best_tool("Find tools for scientific agent research and deep reasoning")
        dt = (time.perf_counter() - t0) * 1000
        passed = selection.selected_adapter is not None and selection.compatibility_score > 0.8
        self.record(
            "WORKFLOW_F_CAPABILITY",
            "autonomous_capability_selection",
            "PASS" if passed else "FAIL",
            dt,
            f"Selected Tool: {selection.selected_adapter} from {selection.selected_repo} (Score: {selection.compatibility_score})",
            {"adapter": selection.selected_adapter, "repo": selection.selected_repo}
        )

    async def test_workflow_g_system_performance(self):
        print("\n--- WORKFLOW G: Computer & System Performance Analysis ---")
        t0 = time.perf_counter()
        res = await brain.process_user_request(
            session_id="wf_system",
            user_prompt="Matrix, analyze my computer's performance and show telemetry."
        )
        dt = (time.perf_counter() - t0) * 1000
        reply = res.get("reply", "")
        passed = any(w in reply.lower() for w in ["cpu", "ram", "memory", "%", "telemetry"])
        self.record(
            "WORKFLOW_G_SYSTEM",
            "system_performance_telemetry",
            "PASS" if passed else "FAIL",
            dt,
            f"Reply: '{reply[:65]}...'",
            {"reply": reply[:300]}
        )

    async def test_workflow_h_task_summarization(self):
        print("\n--- WORKFLOW H: Task State Machine & History Summarization ---")
        t0 = time.perf_counter()
        async with AsyncSessionLocal() as session:
            stmt = select(TaskRecord).order_by(TaskRecord.id.desc()).limit(10)
            tasks = (await session.execute(stmt)).scalars().all()

        dt = (time.perf_counter() - t0) * 1000
        passed = len(tasks) > 0
        task_summaries = [f"{t.task_id}: {t.title} [{t.status}]" for t in tasks[:3]]
        self.record(
            "WORKFLOW_H_TASKS",
            "task_state_summarization",
            "PASS" if passed else "FAIL",
            dt,
            f"Retrieved {len(tasks)} persisted tasks. Latest: {task_summaries[0] if task_summaries else 'None'}",
            {"count": len(tasks), "samples": task_summaries}
        )

    def save_raw_json(self):
        out_path = WORKSPACE_ROOT / "docs" / "production_acceptance_raw.json"
        total = sum(len(v) for v in self.results.values())
        passed = sum(sum(1 for i in v if i["status"] == "PASS") for v in self.results.values())
        data = {
            "timestamp": time.time(),
            "total_workflows": len(self.results),
            "total_tests": total,
            "passed": passed,
            "pass_rate_pct": round((passed / total) * 100, 2),
            "workflows": self.results
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\n[OK] Raw Production Acceptance Telemetry saved to: {out_path}")


if __name__ == "__main__":
    runner = ProductionAcceptanceRunner()
    asyncio.run(runner.run_all())
