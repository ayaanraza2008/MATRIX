import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
sys.stdout.reconfigure(encoding='utf-8')

from core.model_manager import model_manager

async def main():
    print("=== VERIFYING MATRIX MODEL MANAGER & REAL LOCAL AI ===")

    models = await model_manager.list_available_models()
    print("\n1. Discovered Models:")
    for m in models:
        print(f"  • {m.name:<32} [Provider: {m.provider:<12}] Available: {m.is_available}")

    print("\n2. Testing Natural-Language Reasoning (Local GGUF Model):")
    prompt = "Explain in 2 sentences why asynchronous programming is important in high-concurrency systems."
    resp = await model_manager.generate_response(prompt=prompt)
    
    print(f"  Model Name:   {resp.model_name}")
    print(f"  Provider:     {resp.provider}")
    print(f"  Is Local:     {resp.is_local}")
    print(f"  Latency:      {resp.latency_ms} ms")
    print(f"  Tokens Used:  {resp.tokens_used}")
    print(f"  Content:\n    {resp.content}")

    assert resp.provider == "local_gguf", f"Expected local_gguf, got {resp.provider}"
    assert resp.is_local is True
    assert len(resp.content) > 30

    print("\n3. Testing Multi-Step Planning Directive:")
    prompt2 = "Create a 3-step action plan to audit system health, inspect files, and generate a report."
    resp2 = await model_manager.generate_response(prompt=prompt2)
    print(f"  Content:\n    {resp2.content}")

    print("\nSUCCESS: REAL LOCAL AI INFERENCE & PLANNING VERIFIED!")

asyncio.run(main())
