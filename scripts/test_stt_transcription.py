"""Test faster-whisper INT8 CPU transcription."""
import sys
import time
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import soundfile as sf
from voice.speech_to_text.engine import stt_engine

# Generate a small 1-second 16kHz sine wave test file
test_wav = Path(r"D:\matrix_data\cache\test_stt_tone.wav")
test_wav.parent.mkdir(parents=True, exist_ok=True)
data = (np.sin(np.linspace(0, 440 * 2 * np.pi, 16000)) * 10000).astype(np.int16)
sf.write(str(test_wav), data, 16000)

print("Testing STT engine model load & transcribe...")
t0 = time.perf_counter()
res = stt_engine._transcribe_sync(str(test_wav))
elapsed = round((time.perf_counter() - t0) * 1000, 2)

print(f"STT Result in {elapsed}ms:")
print("  - Text:", repr(res.get("text")))
print("  - Detected language:", res.get("detected_language"))
print("  - Language prob:", res.get("language_probability"))
if "error" in res:
    print("  - Error:", res["error"])
else:
    print("STT Engine loaded and functional on CPU INT8!")

if test_wav.exists():
    test_wav.unlink()
