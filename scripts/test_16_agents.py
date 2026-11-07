import asyncio
import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.brain import brain

prompts = [
    ('computer', 'Run safe command whoami on computer'),
    ('browser', 'Search the web for latest AI agents using browser capability'),
    ('research', 'Perform deep research on quantum computing and compile a research report'),
    ('coding', 'Analyze the Python file core/brain.py using coding capability'),
    ('files', 'List personal files in storage partition'),
    ('voice', 'Speak out loud using voice: Acceptance test initiated'),
    ('vision', 'Inspect the screen contents using vision'),
    ('android', 'Generate Android companion pairing token'),
    ('system', 'Inspect computer hardware using system telemetry'),
    ('personal', 'Who are you and what are your capabilities?'),
    ('automation', 'Schedule an automated workflow task for system check'),
    ('creative', 'Create a Mermaid architecture diagram of the system'),
    ('memory', 'Save my favorite food as Pizza in memory'),
    ('repo_intel', 'Inspect starred repositories inventory'),
    ('security', 'Inspect security policy and evaluate command payload echo test'),
    ('data_analysis', 'Perform data analysis on numerical dataset and calculate stats')
]

async def main():
    print(f"{'AGENT':15} | {'STATUS':9} | {'LATENCY':9} | REPLY SNIPPET")
    print("-" * 80)
    for target_ag, prompt in prompts:
        t0 = time.perf_counter()
        res = await brain.process_user_request(session_id="test_16", user_prompt=prompt)
        dt = (time.perf_counter() - t0) * 1000
        status = res.get("plan_status", "UNKNOWN")
        reply = res.get("reply", "").replace("\n", " ")[:60]
        print(f"{target_ag:15} | {status:9} | {dt:7.1f}ms | {reply}")

if __name__ == "__main__":
    asyncio.run(main())
