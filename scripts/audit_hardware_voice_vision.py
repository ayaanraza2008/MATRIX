import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path.cwd()))
sys.stdout.reconfigure(encoding='utf-8')

import cv2
import sounddevice as sd
import numpy as np

print("=== HARDWARE AUDIT: VOICE & VISION ===")

# 1. Audio Devices Audit
print("\n--- 1. Audio Devices Audit ---")
try:
    devices = sd.query_devices()
    default_input = sd.default.device[0]
    default_output = sd.default.device[1]
    print(f"Default Input Device Index: {default_input}")
    print(f"Default Output Device Index: {default_output}")
    print(f"Total Audio Devices detected: {len(devices)}")
    for idx, d in enumerate(devices):
        if d['max_input_channels'] > 0:
            print(f"  [Input {idx}] {d['name']} (Channels: {d['max_input_channels']}, Default SR: {d['default_samplerate']})")
except Exception as e:
    print(f"Audio query error: {e}")

# 2. Microphone Capture Test (1 second buffer)
print("\n--- 2. Microphone Recording Test (1 sec @ 16kHz) ---")
try:
    sr = 16000
    duration = 1.0  # seconds
    print(f"Recording {duration}s from device {default_input}...")
    recording = sd.rec(int(duration * sr), samplerate=sr, channels=1, dtype='float32')
    sd.wait()
    rms = float(np.sqrt(np.mean(recording**2)))
    max_amp = float(np.max(np.abs(recording)))
    print(f"  [SUCCESS] Recorded {len(recording)} samples.")
    print(f"  Audio Energy RMS: {rms:.6f}")
    print(f"  Audio Peak Amplitude: {max_amp:.6f}")
except Exception as e:
    print(f"  [FAILED] Microphone recording failed: {e}")

# 3. Speech Output (TTS) Test
print("\n--- 3. Speech Synthesis (TTS) Test ---")
import asyncio
from voice.text_to_speech.engine import tts_engine

async def test_tts():
    try:
        t0 = time.perf_counter()
        test_file = await tts_engine.speak("MATRIX hardware audit test. Voice subsystem operational.")
        lat = (time.perf_counter() - t0) * 1000
        if test_file and test_file.exists():
            print(f"  [SUCCESS] TTS generated: {test_file.name} ({test_file.stat().st_size} bytes in {lat:.1f}ms)")
        else:
            print(f"  [FAILED] TTS file not created.")
    except Exception as e:
        print(f"  [FAILED] TTS exception: {e}")

asyncio.run(test_tts())

# 4. Physical Camera Hardware Test (cv2.VideoCapture(0))
print("\n--- 4. Physical Camera Hardware Test ---")
try:
    t0 = time.perf_counter()
    cap = cv2.VideoCapture(0)
    opened = cap.isOpened()
    if opened:
        ret, frame = cap.read()
        cap.release()
        lat = (time.perf_counter() - t0) * 1000
        if ret and frame is not None:
            h, w, c = frame.shape
            out_cam = Path("D:/matrix_data/cache/vision/audit_cam_test.jpg")
            out_cam.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(out_cam), frame)
            print(f"  [SUCCESS] Camera device 0 opened: captured frame {w}x{h} (channels: {c}) in {lat:.1f}ms.")
            print(f"  Saved test frame to: {out_cam} ({out_cam.stat().st_size} bytes)")
        else:
            print(f"  [WARNING] Camera opened, but frame read returned False (device busy or no stream).")
    else:
        print(f"  [WARNING] cv2.VideoCapture(0) could not open. Camera might be in use, disabled, or index mismatch.")
except Exception as e:
    print(f"  [ERROR] Camera exception: {e}")

# 5. Desktop Screenshot & Visual Analysis Test
print("\n--- 5. Desktop Screenshot & Visual Analysis Test ---")
try:
    import pyautogui
    from PIL import Image
    t0 = time.perf_counter()
    scr = pyautogui.screenshot()
    out_scr = Path("D:/matrix_data/cache/vision/audit_screen_test.png")
    out_scr.parent.mkdir(parents=True, exist_ok=True)
    scr.save(str(out_scr))
    lat = (time.perf_counter() - t0) * 1000
    print(f"  [SUCCESS] PyAutoGUI screen capture: {scr.size} in {lat:.1f}ms -> {out_scr} ({out_scr.stat().st_size} bytes)")
except Exception as e:
    print(f"  [FALLBACK] PyAutoGUI screen grab exception: {e}")
    # Test virtual buffer
    from PIL import Image, ImageDraw
    fallback_img = Image.new("RGB", (1920, 1080), color=(10, 15, 29))
    draw = ImageDraw.Draw(fallback_img)
    draw.rectangle([(20, 20), (1900, 1060)], outline=(0, 240, 255), width=2)
    draw.text((60, 60), "MATRIX Desktop Monitor [Virtual Display Buffer]", fill=(0, 240, 255))
    out_scr = Path("D:/matrix_data/cache/vision/audit_screen_fallback.png")
    fallback_img.save(str(out_scr))
    print(f"  [SUCCESS] Virtual display buffer generated: 1920x1080 -> {out_scr} ({out_scr.stat().st_size} bytes)")
