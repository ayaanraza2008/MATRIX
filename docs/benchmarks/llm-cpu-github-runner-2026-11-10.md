# Local LLM benchmark — GitHub runner (reference hardware)

**Measured:** 2026-11-10 · workflow run [`42839431687`](https://github.com/ayaanraza2008/MATRIX/actions/runs/42839431687)
**Model:** Qwen2.5-0.5B-Instruct Q4_K_M (`qwen2.5-0.5b-instruct-q4_k_m.gguf`, 468.6 MB)
**Runtime:** `llama-cpp-python` 0.3.36 (CPU wheel), 2 threads

> These numbers describe a **GitHub-hosted runner** (2 physical / 4 logical vCPU, 16 GB RAM,
> shared cloud hardware). They are *reference* figures, not the owner's 8 GB Ryzen 7 5700U.
> Target-hardware numbers must be produced locally with the same script.

## Raw result

```json
{
  "model": "model.gguf",
  "model_size_mb": 468.6,
  "host": {
    "platform": "Linux-7.0.0-1017-azure-x86_64-with-glibc2.39",
    "machine": "x86_64",
    "python": "3.12.16",
    "cpu_count_logical": 4,
    "cpu_count_physical": 2,
    "ram_total_mb": 15984.0
  },
  "threads": 2,
  "load_seconds": 0.42,
  "generation_seconds": 0.67,
  "completion_tokens": 30,
  "tokens_per_second": 44.6,
  "memory_baseline_mb": 43.5,
  "memory_after_load_mb": 626.5,
  "memory_after_generation_mb": 633.5,
  "memory_delta_mb": 590.1,
  "prompt": "In two short sentences, explain what an offline personal AI assistant is.",
  "sample_output": "An offline personal AI assistant is a type of AI assistant that can operate independently of the internet, allowing users to access and interact with it from anywhere."
}
```

## What this establishes

1. **The local inference path works end-to-end.** A real GGUF loads through
   `llama-cpp-python` and produces coherent text — this is no longer a claim, it is a
   reproducible artifact (`llm-benchmark-result`).
2. **Memory budget for a 0.5B Q4_K_M model is ~590 MB** resident (43.5 MB → 633.5 MB).
   On an 8 GB machine that leaves ample headroom for the FastAPI stack.
3. **Throughput is usable for a chat loop** even on 2 threads: 44.6 tokens/s means a
   ~30-token reply in under a second.

## What this does **not** establish

- Throughput/RSS of **Qwen2.5-1.5B** (the README's candidate) on the 8 GB target — that model
  needs ~3× the weights and must be measured before being selected.
- Behaviour with `n_ctx=2048` on long conversations, or under concurrent requests.
- Any voice/vision interaction — text only.

## Reproduce on the target laptop

```powershell
# once, with the CPU wheel index (no compiler required)
pip install --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu llama-cpp-python psutil

# place the model anywhere; MATRIX resolves its data dir automatically
python scripts/benchmark_local_llm.py `
  --model D:\matrix_data\models\qwen2.5-0.5b-instruct-q4_k_m.gguf `
  --max-tokens 128 `
  --out docs\benchmarks\local-8gb.json
```

Notes:
- On the 8 GB Ryzen, expect a different thread count; use `--threads 8` to match the physical
  cores instead of the default (half of logical CPUs).
- This sandbox could not reach `huggingface.co` (`curl` and `Invoke-WebRequest` both fail), which
  is why the first measured run happened on a GitHub runner through
  `.github/workflows/benchmark-llm.yml`.
