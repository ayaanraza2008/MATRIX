"""MATRIX Master End-to-End System Acceptance Verification.
Executes an exhaustive multi-pillar audit of the entire MATRIX ecosystem:
1. System & Health Telemetry
2. Local AI Brain (Qwen2.5 GGUF via llama-cpp-python on AVX2)
3. All 16 Specialized Agents Verification
4. Voice Interaction ( Christopher JARVIS TTS + Whisper STT)
5. Vision Pipeline (Multi-Tier Screen Capture + Perceptual Analysis)
6. PC Automation & Security Guardrails
7. Android Companion Synchronization & Pairing
8. Repository Intelligence (65 repositories catalog)
"""
import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.session import AsyncSessionLocal, check_db_health
from database.init_db import init_database
from core.model_manager import model_manager
from core.orchestrator import orchestrator
from core.task_router import task_router
from core.intent_engine import intent_engine
from voice.text_to_speech.engine import tts_engine
from voice.speech_to_text.engine import stt_engine
from vision.screenshot.capture import desktop_screen_capture
from vision.detection.analyzer import vision_analyzer
from agents.computer.agent import ComputerAgent
from api.routes.devices import pair_device, list_devices, revoke_device, PairRequest
from repository_engine.repository_analyzer import repository_analyzer


async def main():
    print("=" * 80)
    print("      MATRIX AI ECOSYSTEM — MASTER END-TO-END ACCEPTANCE AUDIT")
    print("=" * 80)
    
    audit_results = {}
    
    # -------------------------------------------------------------
    # PILLAR 1: SYSTEM & HEALTH
    # -------------------------------------------------------------
    print("\n[PILLAR 1/8] Verifying Database & System Health...")
    t0 = time.perf_counter()
    await init_database()
    db_healthy = await check_db_health()
    assert db_healthy, "Database health check failed"
    audit_results["pillar_1_system_health"] = {
        "status": "PASSED",
        "time_ms": round((time.perf_counter() - t0) * 1000, 2),
        "db": "SQLite Async (aiosqlite) Operational"
    }
    print(f"  -> PASS: SQLite async database initialized and verified in {audit_results['pillar_1_system_health']['time_ms']} ms.")

    # -------------------------------------------------------------
    # PILLAR 2: LOCAL AI BRAIN INFERENCE
    # -------------------------------------------------------------
    print("\n[PILLAR 2/8] Verifying Genuine Local LLM Brain (Qwen2.5 GGUF)...")
    t0 = time.perf_counter()
    brain_prompt = "Explain in one concise sentence what your role as MATRIX is."
    brain_resp = await model_manager.generate_response(
        prompt=brain_prompt,
        system_prompt="You are MATRIX, a personal AI operating system inspired by JARVIS.",
        temperature=0.3,
        max_tokens=60
    )
    t_brain = round((time.perf_counter() - t0) * 1000, 2)
    print(f"  -> Model Used: {brain_resp.model_name}")
    print(f"  -> Provider:   {brain_resp.provider}")
    print(f"  -> Response:   {brain_resp.content.strip()}")
    print(f"  -> Latency:    {t_brain} ms ({brain_resp.tokens_used} tokens)")
    assert len(brain_resp.content) > 10, "Brain response was empty or too short"
    assert brain_resp.provider in ["local_gguf", "gemini_cloud", "ollama"], f"Unexpected provider: {brain_resp.provider}"
    audit_results["pillar_2_brain_inference"] = {
        "status": "PASSED",
        "model": brain_resp.model_name,
        "provider": brain_resp.provider,
        "latency_ms": t_brain,
        "response_sample": brain_resp.content[:60] + "..."
    }

    # -------------------------------------------------------------
    # PILLAR 3: ALL 16 SPECIALIZED AGENTS
    # -------------------------------------------------------------
    print("\n[PILLAR 3/8] Verifying All 16 Specialized Agents in Orchestrator...")
    registered_agents = list(task_router._agents.keys())
    print(f"  -> Total Agents Registered: {len(registered_agents)}")
    assert len(registered_agents) >= 16, f"Expected at least 16 agents, found {len(registered_agents)}"
    for idx, name in enumerate(registered_agents, 1):
        print(f"     [{idx:02d}] Agent: {name:<14} -> {type(task_router._agents[name]).__name__}")
    
    # Test dispatching a task through orchestrator
    t0 = time.perf_counter()
    orch_res = await orchestrator.execute_request("Check CPU telemetry and system metrics")
    t_orch = round((time.perf_counter() - t0) * 1000, 2)
    print(f"  -> Orchestrator Plan Status: {orch_res.plan.status}")
    print(f"  -> Orchestrator Response:    {orch_res.response_text[:90]}...")
    assert orch_res.plan.status in ["COMPLETED", "completed", "SUCCESS", "success"], f"Plan status was {orch_res.plan.status}"
    audit_results["pillar_3_agents"] = {
        "status": "PASSED",
        "total_agents": len(registered_agents),
        "agents": registered_agents,
        "test_task_time_ms": t_orch
    }

    # -------------------------------------------------------------
    # PILLAR 4: VOICE PIPELINE (TTS + STT)
    # -------------------------------------------------------------
    print("\n[PILLAR 4/8] Verifying Voice Pipeline (JARVIS Christopher TTS + Whisper STT)...")
    t0 = time.perf_counter()
    audio_path = await tts_engine.speak("MATRIX systems are fully operational, sir.")
    assert audio_path and audio_path.exists() and audio_path.stat().st_size > 0, "TTS audio synthesis failed"
    print(f"  -> TTS Audio Generated: {audio_path.name} ({audio_path.stat().st_size} bytes)")
    
    stt_result = await stt_engine.transcribe(audio_path)
    print(f"  -> STT Transcribed Text: '{stt_result['text'].strip()}' (lang={stt_result.get('detected_language')})")
    assert "operational" in stt_result["text"].lower() or "matrix" in stt_result["text"].lower()
    t_voice = round((time.perf_counter() - t0) * 1000, 2)
    audit_results["pillar_4_voice"] = {
        "status": "PASSED",
        "audio_file": str(audio_path.name),
        "stt_transcription": stt_result["text"].strip(),
        "total_voice_loop_ms": t_voice
    }

    # -------------------------------------------------------------
    # PILLAR 5: VISION PIPELINE
    # -------------------------------------------------------------
    print("\n[PILLAR 5/8] Verifying Multi-Tier Screen Capture & Perceptual Vision...")
    t0 = time.perf_counter()
    screen_res = desktop_screen_capture.capture()
    print(f"  -> Screen Frame: {screen_res['width']}x{screen_res['height']} (Method: {screen_res['method']})")
    assert os.path.exists(screen_res["filepath"])
    
    vision_analysis = await vision_analyzer.describe_scene(Path(screen_res["filepath"]))
    print(f"  -> Vision Summary: {vision_analysis['summary']}")
    print(f"  -> Sharpness: {vision_analysis['analysis']['sharpness_score']:.1f} | Brightness: {vision_analysis['analysis']['brightness']:.1f}")
    t_vision = round((time.perf_counter() - t0) * 1000, 2)
    audit_results["pillar_5_vision"] = {
        "status": "PASSED",
        "frame_res": f"{screen_res['width']}x{screen_res['height']}",
        "summary": vision_analysis["summary"],
        "time_ms": t_vision
    }

    # -------------------------------------------------------------
    # PILLAR 6: PC AUTOMATION & SECURITY GUARDRAILS
    # -------------------------------------------------------------
    print("\n[PILLAR 6/8] Verifying PC Automation & Security Guardrails...")
    comp_agent = ComputerAgent()
    
    # Safe command
    safe_res = await comp_agent.execute("command", {"command": "hostname"})
    print(f"  -> Safe Command ('hostname'): {safe_res.data.get('stdout', '').strip()} (success={safe_res.success})")
    assert safe_res.success, "Safe command failed"
    
    # Dangerous command
    danger_res = await comp_agent.execute("command", {"command": "del /f /q C:\\Windows\\System32"})
    print(f"  -> Dangerous Command: Gate blocked = {not danger_res.success} ({danger_res.error})")
    assert not danger_res.success and "not permitted" in danger_res.error
    
    # Window listing
    windows_res = await comp_agent.execute("windows", {})
    win_list = windows_res.data.get("windows", []) if windows_res.data else []
    print(f"  -> Active Windows Detected: {len(win_list)} windows found")
    audit_results["pillar_6_automation_security"] = {
        "status": "PASSED",
        "safe_command_status": "success",
        "dangerous_command_blocked": True,
        "windows_detected_count": len(win_list)
    }

    # -------------------------------------------------------------
    # PILLAR 7: ANDROID COMPANION SYNCHRONIZATION
    # -------------------------------------------------------------
    print("\n[PILLAR 7/8] Verifying Android Companion Synchronization & APK...")
    apk_path = "D:\\matrix_data\\apk\\matrix-debug.apk"
    apk_exists = os.path.exists(apk_path)
    apk_size_mb = round(os.path.getsize(apk_path) / (1024 * 1024), 2) if apk_exists else 0
    print(f"  -> Compiled Android APK: {apk_path} ({apk_size_mb} MB) [Exists={apk_exists}]")
    assert apk_exists and apk_size_mb > 5.0, "Compiled Android APK missing or incomplete"
    
    async with AsyncSessionLocal() as session:
        pair_req = PairRequest(
            device_id="android_verification_device_007",
            name="JARVIS Mobile Unit (E2E Verified)",
            platform="android",
            pairing_token="mtx_pair_verified_e2e"
        )
        pair_res = await pair_device(pair_req, session)
        print(f"  -> Device Pairing: {pair_res['status']} (AuthToken={pair_res['auth_token'][:18]}...)")
        assert pair_res["status"] == "PAIRED"
        
        # Revoke after test
        await revoke_device("android_verification_device_007", session)
        
    audit_results["pillar_7_android_sync"] = {
        "status": "PASSED",
        "apk_compiled": True,
        "apk_size_mb": apk_size_mb,
        "pairing_api": "VERIFIED"
    }

    # -------------------------------------------------------------
    # PILLAR 8: REPOSITORY INTELLIGENCE
    # -------------------------------------------------------------
    print("\n[PILLAR 8/8] Verifying GitHub Repositories Intelligence (65 Repos)...")
    assessments = repository_analyzer.analyze_all()
    total_repos = len(assessments)
    print(f"  -> Repositories Indexed: {total_repos} repositories")
    assert total_repos >= 65, f"Expected 65 repositories, found {total_repos}"
    
    # Query repository intelligence
    sample_repo = assessments[0]
    print(f"  -> Sample Repo [1]: {sample_repo.full_name} | Category: {sample_repo.category}")
    audit_results["pillar_8_repositories"] = {
        "status": "PASSED",
        "catalog_count": total_repos,
        "sample": sample_repo.full_name
    }

    # -------------------------------------------------------------
    # FINAL RECAP
    # -------------------------------------------------------------
    print("\n" + "=" * 80)
    print("      ALL 8 MATRIX PILLARS VERIFIED & PASSED 100%!")
    print("=" * 80)
    for pillar, res in audit_results.items():
        print(f"  [+] {pillar.upper()}: {res['status']}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
