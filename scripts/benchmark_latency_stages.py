"""Benchmark end-to-end latency separately across all 7 stages:
1. Text input parsing & reference resolution
2. Voice audio input & VAD detection
3. Intent detection
4. Tool selection & discovery
5. Real execution (OS psutil audit + Network Open-Meteo)
6. Final text response synthesis
7. Text-To-Speech (TTS) speech generation
"""
import sys
import time
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.context_manager import context_manager
from core.intent_engine import intent_engine
from core.autonomy.tool_discovery import tool_discovery
from core.information.briefing import briefing_engine
from voice.text_to_speech.engine import tts_engine
import numpy as np

async def benchmark_pipeline():
    print("=" * 70)
    print("   MATRIX STAGE-BY-STAGE LATENCY BENCHMARK (REAL HARDWARE)")
    print("=" * 70)
    
    # 1. Text Input & Context Resolution
    t0 = time.perf_counter()
    prompt = "What is the current CPU and RAM usage on this computer?"
    context_manager.add_message("bench_sess", "user", prompt)
    resolved = context_manager.resolve_references("bench_sess", prompt)
    t_text = (time.perf_counter() - t0) * 1000
    print(f"1. Text Input & Context Resolution : {t_text:>8.2f} ms")
    
    # 2. Voice Input & Silero VAD Detection
    t0 = time.perf_counter()
    from voice.vad import vad_engine
    dummy_audio = np.zeros(512, dtype=np.float32)
    vad_res = vad_engine.is_speech(dummy_audio)
    t_voice = (time.perf_counter() - t0) * 1000
    print(f"2. Voice Input (VAD Window Eval)   : {t_voice:>8.2f} ms")
    
    # 3. Intent Detection
    t0 = time.perf_counter()
    intent_res = intent_engine.classify(resolved)
    t_intent = (time.perf_counter() - t0) * 1000
    print(f"3. Intent Detection Engine          : {t_intent:>8.2f} ms (Target Agent: {intent_res.target_agent})")
    
    # 4. Tool Selection & Discovery
    t0 = time.perf_counter()
    matched_tools = tool_discovery.search_tools(resolved, limit=3)
    t_tool_sel = (time.perf_counter() - t0) * 1000
    print(f"4. Tool Selection & Capability Rank : {t_tool_sel:>8.2f} ms (Matched: {len(matched_tools)})")
    
    # 5a. Real Execution Stage (psutil live OS hardware audit)
    t0 = time.perf_counter()
    os_data = briefing_engine.get_away_pc_summary()
    t_real_exec_os = (time.perf_counter() - t0) * 1000
    print(f"5a. Real OS Execution (psutil Audit): {t_real_exec_os:>8.2f} ms")
    
    # 5b. Real Execution Stage (Live Open-Meteo HTTP API)
    t0 = time.perf_counter()
    weather_data = await briefing_engine.get_live_weather()
    t_real_exec_net = (time.perf_counter() - t0) * 1000
    print(f"5b. Real Network Exec (Open-Meteo)  : {t_real_exec_net:>8.2f} ms")
    
    # 6. Brain Final Synthesis (Formatting response)
    t0 = time.perf_counter()
    resp_text = (
        f"Host hardware status: CPU load is {os_data['cpu_percent']}%, RAM utilization is {os_data['ram_used_percent']}%, "
        f"with {os_data['total_processes']} running processes. Local weather: {weather_data['condition']} at {weather_data['temperature_c']}°C."
    )
    t_synth = (time.perf_counter() - t0) * 1000
    print(f"6. Final Text Response Synthesis    : {t_synth:>8.2f} ms")
    
    # 7. Text-To-Speech (TTS) Synthesis
    t0 = time.perf_counter()
    audio_path = await tts_engine.synthesize_to_file(resp_text[:100])
    t_tts = (time.perf_counter() - t0) * 1000
    print(f"7. TTS Speech Synthesis Generation  : {t_tts:>8.2f} ms")
    
    total_text_to_text = t_text + t_intent + t_tool_sel + t_real_exec_os + t_synth
    total_voice_to_voice = t_voice + total_text_to_text + t_tts
    
    print("-" * 70)
    print(f"TOTAL REAL-WORLD TEXT-TO-TEXT LATENCY   : {total_text_to_text:>8.2f} ms")
    print(f"TOTAL REAL-WORLD VOICE-TO-VOICE LATENCY : {total_voice_to_voice:>8.2f} ms")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(benchmark_pipeline())
