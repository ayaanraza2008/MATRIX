import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
"""Test script verifying all 14 sample autonomous directives from Phase 10."""
import asyncio
import time
from core.brain import brain

TEST_COMMANDS = [
    ("1. Open Dev Environment", "open my development environment"),
    ("2. Check Email", "check my email and summarize important messages"),
    ("3. Calendar Agenda", "what is on my calendar today"),
    ("4. Monitor Server", "monitor my server"),
    ("5. Outbound Phone Call", "call me in 10 minutes"),
    ("6. PC Activity Explanation", "explain what is happening on my computer"),
    ("7. Daily Briefing", "prepare a daily briefing"),
    ("8. Project Diagnostic", "find the problem in my project and investigate it"),
    ("9. File Organization", "organize these files"),
    ("10. Check Integrations", "check whether all my connected integrations are working"),
    ("11. Outside Remote Briefing", "I am outside. Tell me important updates"),
    ("12. Connect Google Account", "connect my authorized Google account"),
    ("13. Pause Background Tasks", "pause all background tasks"),
    ("14. Stop Remote Access", "stop remote access"),
]

async def run_tests():
    print("=" * 70)
    print("  VERIFYING PHASE 10: 14 AUTONOMOUS OPERATING COMMANDS")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for title, cmd in TEST_COMMANDS:
        t0 = time.perf_counter()
        try:
            res = await brain.process_user_request(session_id="test_sess", user_prompt=cmd)
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            reply = res.get("response", "")
            status = res.get("plan_status", "UNKNOWN")
            
            assert len(reply) > 10, f"Empty reply for '{cmd}'"
            print(f"[PASS] {title:<28} | {duration_ms:>6.1f}ms | Status: {status}")
            print(f"       -> \"{reply[:80]}...\"")
            passed += 1
        except Exception as e:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            print(f"[FAIL] {title:<28} | {duration_ms:>6.1f}ms | Error: {e}")
            failed += 1

    print("=" * 70)
    print(f"RESULTS: {passed}/{len(TEST_COMMANDS)} PASSED | {failed} FAILED")
    print("=" * 70)
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(run_tests())
    exit(0 if success else 1)
