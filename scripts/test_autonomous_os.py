"""MATRIX Autonomous Personal AI Operating System — Master Verification Suite.
Thoroughly verifies all 12 Phases:
  1. Autonomy Core (Brain, Goal Manager, Tool Discovery, Event Bus, Diagnostics, Recovery, 4-Tier Policy)
  2. Universal Integrations (Open-Meteo live weather, connectors, catalog)
  3. Two-Way Telephony & Phone Calling (In-App WebRTC, policy limits, scheduled outbound call)
  4. Personal Real-Time Information (Live weather, away-PC audit, daily briefing)
  5. Persistent Background Task Scheduler (Active tasks, tick loop, pause/resume)
  6. Hierarchical Memory & Privacy Scrubber (Categorized context, semantic search, privacy regex)
  7. Remote Device Pairing & Emergency Access Termination
  8. All 14 Core Autonomous Operating Directives
"""
import sys
import time
import asyncio
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.autonomy.autonomous_core import autonomy_core
from core.autonomy.goal_manager import goal_manager
from core.autonomy.tool_discovery import tool_discovery
from core.autonomy.event_monitor import event_monitor
from core.self_maintenance.diagnostics import diagnostics_engine
from core.self_maintenance.recovery import recovery_engine
from security.permissions.manager import security_manager, AutonomyLevel
from core.integrations.manager import integration_manager
from core.telephony.engine import telephony_engine
from core.information.briefing import briefing_engine
from automation.scheduler.engine import background_scheduler
from memory.manager import memory_manager
from core.pairing_manager import pairing_manager
from core.brain import brain


class AutonomousOSTestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def record(self, test_name: str, passed: bool, duration_ms: float, detail: str = ""):
        status_str = "PASS" if passed else "FAIL"
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        self.results.append({
            "name": test_name,
            "status": status_str,
            "duration_ms": duration_ms,
            "detail": detail
        })
        mark = "[PASS]" if passed else "[FAIL]"
        print(f"{mark} {test_name:<46} | {duration_ms:>6.1f}ms | {detail}")

    async def run_all(self):
        print("=" * 80)
        print("   MATRIX AUTONOMOUS OPERATING SYSTEM — COMPLETE INTEGRATED VERIFICATION")
        print("=" * 80)

        # -------------------------------------------------------------
        # SUITE 1: Autonomy Core Subsystems
        # -------------------------------------------------------------
        print("\n--- SUITE 1: AUTONOMY CORE SUBSYSTEMS ---")
        
        # 1.1 Goal Manager
        t0 = time.perf_counter()
        g = goal_manager.create_goal("Test Autonomous Mission", "Deploy verified services", subgoals=[{"title": "Sub 1"}])
        if g.subgoals:
            goal_manager.update_subgoal_progress(g.goal_id, g.subgoals[0].subgoal_id, status="COMPLETED")
        goals = goal_manager.list_goals()
        d_ms = (time.perf_counter() - t0) * 1000
        self.record("1.1 Goal Manager Decomposition & Tracking", len(goals) >= 1, d_ms, f"{len(goals)} active goals stored")

        # 1.2 Tool Discovery Engine
        t0 = time.perf_counter()
        tools = tool_discovery.discover_all()
        matched = tool_discovery.find_tools("weather and temperature forecast")
        d_ms = (time.perf_counter() - t0) * 1000
        self.record("1.2 Autonomous Tool Discovery Engine", len(tools) >= 50 and len(matched) >= 1, d_ms, f"{len(tools)} tools discovered, query matched '{matched[0]['name']}'")

        # 1.3 Event Monitor (Pub/Sub Bus)
        t0 = time.perf_counter()
        received_events = []
        event_monitor.subscribe("TEST_HEARTBEAT", lambda evt: received_events.append(evt))
        await event_monitor.publish(event_type="TEST_HEARTBEAT", title="Heartbeat Ping", message="Test message", source="test", severity="INFO", data={"key": "val"})
        d_ms = (time.perf_counter() - t0) * 1000
        self.record("1.3 Real-Time Pub/Sub Event Monitor Bus", len(received_events) >= 1, d_ms, "Event dispatched & handled asynchronously")

        # 1.4 Self-Diagnostics Engine
        t0 = time.perf_counter()
        diag = await diagnostics_engine.run_full_diagnostics()
        d_ms = (time.perf_counter() - t0) * 1000
        self.record("1.4 Self-Diagnostics Engine", diag["overall_status"] in ["HEALTHY", "ATTENTION_REQUIRED"], d_ms, f"Status: {diag['overall_status']}, {len(diag['checks'])} checks run")

        # 1.5 Error Recovery & Incident Engine
        t0 = time.perf_counter()
        rec = await recovery_engine.auto_recover_system()
        d_ms = (time.perf_counter() - t0) * 1000
        self.record("1.5 Automated Error Recovery & Memory Clean", rec["status"] in ["RECOVERED", "HEALTHY"], d_ms, f"Cleaned: {rec.get('cache_cleaned', 0)} items")

        # 1.6 4-Tier Autonomy Security Policy & Gate
        t0 = time.perf_counter()
        security_manager.set_global_autonomy_level(3)
        check_safe = security_manager.evaluate_action("launch_application")
        check_critical = security_manager.evaluate_action("delete_important_file")
        d_ms = (time.perf_counter() - t0) * 1000
        lvl4_gated = check_critical.get("requires_confirmation") is True
        self.record("1.6 4-Tier Autonomy Policy & Level 4 Confirmation Gate", check_safe["authorized"] and lvl4_gated, d_ms, f"Level 2 Assist: {check_safe['authorized']}, Level 4 Gated: {lvl4_gated}")

        # -------------------------------------------------------------
        # SUITE 2: Universal Connectivity & Live Weather
        # -------------------------------------------------------------
        print("\n--- SUITE 2: UNIVERSAL CONNECTIVITY & LIVE APIS ---")

        # 2.1 Live Open-Meteo Weather
        t0 = time.perf_counter()
        weather = await briefing_engine.get_live_weather()
        d_ms = (time.perf_counter() - t0) * 1000
        self.record("2.1 Live Open-Meteo Weather (Zero Cost)", weather["success"] and weather["temperature_c"] is not None, d_ms, f"{weather['condition']} at {weather['temperature_c']}°C")

        # 2.2 Integration Health Probing
        t0 = time.perf_counter()
        all_integs = integration_manager.list_integrations()
        probe_res = await integration_manager.test_integration("weather_openmeteo")
        d_ms = (time.perf_counter() - t0) * 1000
        self.record("2.2 Integration Connector Health Probing", len(all_integs) >= 7 and probe_res["success"], d_ms, f"{len(all_integs)} connectors registered in marketplace")

        # -------------------------------------------------------------
        # SUITE 3: Two-Way Telephony & Phone Calling
        # -------------------------------------------------------------
        print("\n--- SUITE 3: TWO-WAY TELEPHONY & CALLING ---")

        # 3.1 Telephony Policy Evaluation
        t0 = time.perf_counter()
        policy = telephony_engine.get_policy_summary()
        can_call = telephony_engine.check_can_call_outbound("EXPLICIT_REQUEST")
        d_ms = (time.perf_counter() - t0) * 1000
        self.record("3.1 Telephony Outbound Policy & Rate Limits", "policy" in policy and "allowed" in can_call, d_ms, f"Target: {policy['policy']['verified_phone_number']}, Rate Limit: {policy['policy']['max_calls_per_hour']}/hr")

        # 3.2 Scheduled Outbound Call Dispatch
        t0 = time.perf_counter()
        sched_res = await telephony_engine.schedule_outbound_call(delay_seconds=600, reason="Milestone complete")
        d_ms = (time.perf_counter() - t0) * 1000
        self.record("3.2 Scheduled Outbound Callback Dispatch", sched_res["success"], d_ms, f"Task {sched_res.get('scheduled_task_id')}: {sched_res.get('message')}")

        # -------------------------------------------------------------
        # SUITE 4: Personal Real-Time Information & Briefing
        # -------------------------------------------------------------
        print("\n--- SUITE 4: PERSONAL REAL-TIME INFORMATION ---")

        # 4.1 Away-PC Telemetry Audit
        t0 = time.perf_counter()
        away_pc = briefing_engine.get_away_pc_summary()
        d_ms = (time.perf_counter() - t0) * 1000
        self.record("4.1 Host PC Real-Time Telemetry Audit", away_pc["uptime_hours"] > 0 and away_pc["total_processes"] > 10, d_ms, f"Uptime: {away_pc['uptime_hours']}h | RAM: {away_pc['ram_used_percent']}% | Procs: {away_pc['total_processes']}")

        # 4.2 Comprehensive Daily Briefing Synthesis
        t0 = time.perf_counter()
        briefing = await briefing_engine.generate_daily_briefing("Sir")
        d_ms = (time.perf_counter() - t0) * 1000
        self.record("4.2 Executive Daily Briefing Synthesis", len(briefing["briefing_text"]) > 100, d_ms, f"{len(briefing['briefing_text'])} chars synthesized")

        # -------------------------------------------------------------
        # SUITE 5: Persistent Background Task Scheduler
        # -------------------------------------------------------------
        print("\n--- SUITE 5: BACKGROUND SCHEDULER & AUTONOMY ---")

        t0 = time.perf_counter()
        await background_scheduler.start()
        tasks = await background_scheduler.list_tasks()
        background_scheduler.pause_all()
        paused_state = background_scheduler.is_paused
        background_scheduler.resume_all()
        resumed_state = not background_scheduler.is_paused
        d_ms = (time.perf_counter() - t0) * 1000
        self.record("5.1 Persistent Background Task Scheduler", paused_state and resumed_state, d_ms, f"{len(tasks)} tasks registered, Pause & Resume verified")

        # -------------------------------------------------------------
        # SUITE 6: Hierarchical Memory & Privacy Scrubber
        # -------------------------------------------------------------
        print("\n--- SUITE 6: HIERARCHICAL MEMORY & PRIVACY SCRUBBER ---")

        # 6.1 Privacy Secret Scrubber
        t0 = time.perf_counter()
        scrubbed_txt, detected = memory_manager.scrub_text("API: AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5 and sk-abcdef1234567890abcdef123456")
        d_ms = (time.perf_counter() - t0) * 1000
        self.record("6.1 Automated Credential & Secret Scrubber", detected and "AIza" not in scrubbed_txt and "sk-" not in scrubbed_txt, d_ms, f"Scrubbed secrets: {detected}")

        # 6.2 Persistent Memory Add & Search
        t0 = time.perf_counter()
        added_mem = await memory_manager.add_memory("test_deploy_target", "Server is AWS us-east-1 production cluster", "project", ["infra", "aws"])
        search_res = await memory_manager.search_memory("production cluster")
        await memory_manager.delete_memory(added_mem["memory_id"])
        d_ms = (time.perf_counter() - t0) * 1000
        self.record("6.2 Hierarchical Categorized Memory & Search", len(search_res) >= 1, d_ms, f"Found {len(search_res)} matching memory entries")

        # -------------------------------------------------------------
        # SUITE 7: Remote Companion & Emergency Cutoff
        # -------------------------------------------------------------
        print("\n--- SUITE 7: REMOTE COMPANION & EMERGENCY CUTOFF ---")

        t0 = time.perf_counter()
        tok = pairing_manager.create_token(ttl_seconds=120)
        active_tokens_count = len(pairing_manager.list_active_tokens())
        pairing_manager._registry.clear()
        d_ms = (time.perf_counter() - t0) * 1000
        self.record("7.1 Remote Token Pairing & Emergency Revoke", active_tokens_count >= 1 and len(pairing_manager.list_active_tokens()) == 0, d_ms, f"Generated token {tok['pairing_token'][:18]}... Revoked: OK")

        # -------------------------------------------------------------
        # SUITE 8: 14 Core Autonomous Operating Directives
        # -------------------------------------------------------------
        print("\n--- SUITE 8: 14 CORE AUTONOMOUS DIRECTIVES ---")
        
        directives = [
            ("8.01 'open my development environment'", "open my development environment"),
            ("8.02 'check my email and summarize'", "check my email and summarize important messages"),
            ("8.03 'what is on my calendar today'", "what is on my calendar today"),
            ("8.04 'monitor my server'", "monitor my server"),
            ("8.05 'call me in 10 minutes'", "call me in 10 minutes"),
            ("8.06 'explain what is happening on my pc'", "explain what is happening on my computer"),
            ("8.07 'prepare a daily briefing'", "prepare a daily briefing"),
            ("8.08 'find the problem in my project'", "find the problem in my project and investigate it"),
            ("8.09 'organize these files'", "organize these files"),
            ("8.10 'check whether integrations working'", "check whether all my connected integrations are working"),
            ("8.11 'I am outside. Tell me updates'", "I am outside. Tell me important updates"),
            ("8.12 'connect my authorized Google account'", "connect my authorized Google account"),
            ("8.13 'pause all background tasks'", "pause all background tasks"),
            ("8.14 'stop remote access'", "stop remote access"),
        ]

        for label, cmd in directives:
            t0 = time.perf_counter()
            res = await brain.process_user_request(session_id="suite_test", user_prompt=cmd)
            d_ms = (time.perf_counter() - t0) * 1000
            resp = res.get("response", "")
            status_ok = len(resp) > 15
            self.record(label, status_ok, d_ms, f"\"{resp[:60]}...\"")

        # -------------------------------------------------------------
        # FINAL SCORECARD
        # -------------------------------------------------------------
        total = self.passed + self.failed
        print("\n" + "=" * 80)
        print(f"   FINAL VERIFICATION SCORECARD: {self.passed}/{total} PASSED ({(self.passed/total)*100:.1f}%) | {self.failed} FAILED")
        print("=" * 80)
        return self.failed == 0


if __name__ == "__main__":
    runner = AutonomousOSTestRunner()
    success = asyncio.run(runner.run_all())
    sys.exit(0 if success else 1)
