"""Test Qwen2.5 0.5B Local Model on the 7 User Directives."""
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.model_manager import model_manager

TEST_PROMPTS = [
    "Hello MATRIX, introduce yourself.",
    "What can you do?",
    "Explain what is running on my computer.",
    "Create a Python calculator.",
    "Read a file and summarize it.",
    "Plan a multi-step task.",
    "Answer this question in Hinglish: How are you today and what are you working on?"
]

async def eval_prompts():
    print("=" * 70)
    print("EVALUATING LOCAL LLM (Qwen2.5 0.5B GGUF) ON USER DIRECTIVES")
    print("=" * 70)
    
    for idx, prompt in enumerate(TEST_PROMPTS, 1):
        print(f"\n--- PROMPT {idx}: '{prompt}' ---")
        t0 = time.perf_counter()
        res = await model_manager.generate_response(
            prompt=prompt,
            system_prompt=(
                "You are MATRIX, an intelligent, calm, professional, and conversational "
                "personal AI operating system inspired by JARVIS from Iron Man. "
                "You understand English, Hindi, and Hinglish. Answer clearly and concisely."
            ),
            temperature=0.3,
            max_tokens=200
        )
        latency = round((time.perf_counter() - t0) * 1000, 2)
        print(f"Provider: {res.provider} | Model: {res.model_name}")
        print(f"Tokens: {res.tokens_used} | Latency: {latency} ms")
        print(f"Response:\n{res.content.strip()}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(eval_prompts())
