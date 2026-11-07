import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
sys.stdout.reconfigure(encoding='utf-8')

print("=== SPEECH-TO-TEXT AUDIT ===")
from voice.speech_to_text.engine import STTEngine
import asyncio

async def test_stt():
    stt = STTEngine()
    stt.model_size = "tiny"  # ~40 MB
    audio_files = list(Path("D:/matrix_data/cache/audio").glob("*.mp3"))
    if not audio_files:
        print("No audio files found to transcribe.")
        return
    latest_audio = sorted(audio_files, key=lambda p: p.stat().st_mtime)[-1]
    print(f"Transcribing {latest_audio} ({latest_audio.stat().st_size} bytes)...")
    res = await stt.transcribe(latest_audio)
    print(f"STT Result: {res}")

asyncio.run(test_stt())
