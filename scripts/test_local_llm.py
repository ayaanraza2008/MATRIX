import sys
import time
import os
import psutil
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

print("=== MATRIX LOCAL LLM INFERENCE TEST ===")

MODEL_PATH = "D:/matrix_data/models/qwen2.5-0.5b-instruct-q4_k_m.gguf"
if not os.path.exists(MODEL_PATH):
    print(f"Error: Model file does not exist at {MODEL_PATH}")
    sys.exit(1)

file_mb = os.path.getsize(MODEL_PATH) / (1024*1024)
print(f"Model GGUF file: {MODEL_PATH} ({file_mb:.2f} MB)")

# Check RAM before load
vm_before = psutil.virtual_memory()
print(f"RAM before load: Used {vm_before.used / (1024**2):.1f} MB, Available {vm_before.available / (1024**2):.1f} MB ({vm_before.percent}%)")

from llama_cpp import Llama

t0 = time.perf_counter()
print("Loading model into Llama instance (AVX2 CPU, 4 threads)...")
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=2048,
    n_threads=4,
    verbose=False
)
load_time = time.perf_counter() - t0
print(f"Model loaded successfully in {load_time:.2f}s!")

# Check RAM after load
vm_after = psutil.virtual_memory()
ram_consumed = (vm_after.used - vm_before.used) / (1024**2)
print(f"RAM after load: Used {vm_after.used / (1024**2):.1f} MB (Delta: {ram_consumed:.1f} MB), Available {vm_after.available / (1024**2):.1f} MB")

# Prompt test
prompt = "Who are you and what are your capabilities as the MATRIX AI assistant? Provide a concise 2-sentence response."
print(f"\nUser Prompt: '{prompt}'")

t1 = time.perf_counter()
output = llm.create_chat_completion(
    messages=[
        {"role": "system", "content": "You are MATRIX, a highly capable JARVIS-inspired personal AI assistant for PC and Android."},
        {"role": "user", "content": prompt}
    ],
    max_tokens=128,
    temperature=0.7
)
gen_time = time.perf_counter() - t1

response_text = output["choices"][0]["message"]["content"]
tokens = output["usage"]["completion_tokens"]
tps = tokens / gen_time if gen_time > 0 else 0

print(f"\n--- MODEL RESPONSE ({tokens} tokens in {gen_time:.2f}s @ {tps:.1f} tok/s) ---")
print(response_text)
print("---------------------------------------------------------------")
print("VERDICT: GENUINE LOCAL LLM INFERENCE OPERATIONAL!")
