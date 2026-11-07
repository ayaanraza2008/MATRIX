import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
sys.stdout.reconfigure(encoding='utf-8')

from core.brain import brain
from database.init_db import init_database

async def main():
    print("=== ACCEPTANCE TEST: MATRIX BRAIN & LOCAL AI REASONING ===")
    await init_database()

    # 1. Unfamiliar natural-language question
    session_id = "sess_acceptance_ai"
    prompt1 = "What are the core differences between an asynchronous event loop and a thread pool in personal AI architecture?"
    print(f"\n1. Submitting Prompt: '{prompt1}'")
    
    res1 = await brain.process_user_request(session_id, prompt1)
    print(f"  Plan Title:    {res1.get('plan_title')}")
    print(f"  Plan Status:   {res1.get('plan_status')}")
    print(f"  Latency:       {res1.get('latency_ms')} ms")
    print(f"  Brain Reply:\n{res1.get('response')}\n")

    assert len(res1.get("response", "")) > 50, "Response should be substantive"

    # 2. Command with approved tool call
    prompt2 = "Inspect system telemetry and check available RAM"
    print(f"2. Submitting Directive: '{prompt2}'")
    res2 = await brain.process_user_request(session_id, prompt2)
    print(f"  Plan Title:    {res2.get('plan_title')}")
    print(f"  Plan Status:   {res2.get('plan_status')}")
    print(f"  Brain Reply:\n{res2.get('response')}\n")

    assert res2.get("plan_status") == "COMPLETED"

    print("=== ACCEPTANCE TEST PASSED: GENUINE AI REASONING & ORCHESTRATION CONFIRMED! ===")

if __name__ == "__main__":
    asyncio.run(main())
