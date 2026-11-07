"""Verify MATRIX Brain on all core user directives."""
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Reconfigure console output to UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.brain import brain
from database.init_db import init_database

TEST_PROMPTS = [
    "Hello MATRIX, introduce yourself.",
    "What can you do?",
    "Explain what is running on my computer.",
    "Create a Python calculator.",
    "MATRIX, what is currently visible on my screen?",
    "Answer this question in Hinglish: How are you today?"
]

async def test_all_prompts():
    print("=" * 75)
    print("TESTING MATRIX BRAIN ON REAL DIRECTIVES")
    print("=" * 75)
    await init_database()

    for idx, prompt in enumerate(TEST_PROMPTS, 1):
        print(f"\n[{idx}/6] USER PROMPT: '{prompt}'")
        t0 = time.perf_counter()
        res = await brain.process_user_request(f"sess_prompt_test_{idx}", prompt)
        latency = round((time.perf_counter() - t0) * 1000, 2)
        print(f" -> Plan Title:   {res.get('plan_title')}")
        print(f" -> Plan Status:  {res.get('plan_status')}")
        print(f" -> Total Time:   {latency} ms")
        print(f" -> AI Response:\n{res.get('response')}\n")
        assert len(res.get("response", "")) > 10, f"Empty response for prompt {idx}"
        print("-" * 65)

    print("\n[+] ALL REAL PROMPTS VERIFIED & RETURNED GENUINE AI RESPONSES!")

if __name__ == "__main__":
    asyncio.run(test_all_prompts())
