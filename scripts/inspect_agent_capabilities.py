import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
from core.task_router import task_router

async def inspect():
    for name, agent in task_router._agents.items():
        caps = agent.declare_capabilities()
        cap_summary = []
        for c in caps:
            cap_summary.append(f"{c.name}: {c.operations}")
        print(f"[{name.upper()}] (Autonomy Level {agent.max_autonomy_level}):")
        print(f"  Description: {agent.description}")
        print(f"  Capabilities ({len(caps)}):")
        for cs in cap_summary:
            print(f"    - {cs}")
        print("-" * 60)

if __name__ == "__main__":
    asyncio.run(inspect())
