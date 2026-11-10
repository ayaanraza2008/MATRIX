"""Benchmark a local GGUF model on CPU.

Reports honest, measured numbers: model load time, completion tokens/second and process
memory. Nothing here is estimated or extrapolated — if the model cannot be loaded the
script exits non-zero instead of printing a placeholder result.

Usage:
    python scripts/benchmark_local_llm.py --model path/to/model.gguf --out results.json
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path

import psutil


def _process_memory_mb() -> float:
    proc = psutil.Process()
    try:
        return proc.memory_full_info().uss / (1024 * 1024)
    except (psutil.AccessDenied, AttributeError):
        return proc.memory_info().rss / (1024 * 1024)


def main() -> int:
    parser = argparse.ArgumentParser(description="MATRIX local LLM benchmark")
    parser.add_argument("--model", required=True, help="Path to a .gguf model file")
    parser.add_argument(
        "--prompt",
        default="In two short sentences, explain what an offline personal AI assistant is.",
    )
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--threads", type=int, default=0, help="0 = half of logical CPUs")
    parser.add_argument("--out", default="", help="Optional path for the JSON result")
    args = parser.parse_args()

    model_path = Path(args.model)
    if not model_path.is_file():
        print(f"ERROR: model file not found: {model_path}", file=sys.stderr)
        return 2

    try:
        from llama_cpp import Llama
    except Exception as exc:  # pragma: no cover - environment dependent
        print(f"ERROR: llama-cpp-python is not usable: {exc}", file=sys.stderr)
        return 3

    threads = args.threads or max(1, (psutil.cpu_count(logical=True) or 2) // 2)
    baseline_mb = _process_memory_mb()

    load_start = time.perf_counter()
    llm = Llama(
        model_path=str(model_path),
        n_ctx=2048,
        n_threads=threads,
        verbose=False,
    )
    load_seconds = time.perf_counter() - load_start
    loaded_mb = _process_memory_mb()

    gen_start = time.perf_counter()
    output = llm.create_chat_completion(
        messages=[{"role": "user", "content": args.prompt}],
        max_tokens=args.max_tokens,
        temperature=0.7,
    )
    gen_seconds = time.perf_counter() - gen_start

    text = output["choices"][0]["message"]["content"].strip()
    usage = output.get("usage", {}) or {}
    completion_tokens = int(usage.get("completion_tokens") or 0)
    after_mb = _process_memory_mb()

    result = {
        "model": model_path.name,
        "model_size_mb": round(model_path.stat().st_size / (1024 * 1024), 1),
        "host": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "cpu_count_physical": psutil.cpu_count(logical=False),
            "ram_total_mb": round(psutil.virtual_memory().total / (1024 * 1024), 0),
        },
        "threads": threads,
        "load_seconds": round(load_seconds, 2),
        "generation_seconds": round(gen_seconds, 2),
        "completion_tokens": completion_tokens,
        "tokens_per_second": round(completion_tokens / gen_seconds, 2) if gen_seconds else None,
        "memory_baseline_mb": round(baseline_mb, 1),
        "memory_after_load_mb": round(loaded_mb, 1),
        "memory_after_generation_mb": round(after_mb, 1),
        "memory_delta_mb": round(after_mb - baseline_mb, 1),
        "prompt": args.prompt,
        "sample_output": text[:500],
    }

    rendered = json.dumps(result, indent=2)
    print(rendered)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(rendered, encoding="utf-8")
        print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
