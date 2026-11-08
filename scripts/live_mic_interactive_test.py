"""MATRIX Interactive Real Microphone Hardware Test.
Provides an interactive real-time test console for the user to perform physical
voice and finger-snap actions directly on their Windows 11 machine.
"""
import sys
import os
import time
import asyncio
from pathlib import Path
import numpy as np
import sounddevice as sd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from voice.wake_word.engine import wake_word_detector
from voice.snap_detector import snap_detector
from voice.speech_to_text.engine import stt_engine
from voice.text_to_speech.engine import tts_engine
from voice.conversation.manager import hands_free_manager, ConversationMode, HandsFreeState
from core.brain import brain


async def interactive_test():
    print("=" * 80)
    print("    MATRIX — INTERACTIVE PHYSICAL MICROPHONE ACCEPTANCE SESSION")
    print("=" * 80)
    
    in_dev = sd.default.device[0]
    out_dev = sd.default.device[1]
    in_name = sd.query_devices(in_dev)["name"]
    out_name = sd.query_devices(out_dev)["name"]

    print(f"[i] Microphone Device : [{in_dev}] {in_name}")
    print(f"[i] Speaker Device    : [{out_dev}] {out_name}")
    print("\nPress ENTER when ready to begin the interactive test...")
    # non-blocking or short wait if headless
    try:
        if sys.stdin.isatty():
            input()
    except Exception:
        pass

    chunk_size = 1280
    sr = 16000

    # ---------------------------------------------------------
    # STAGE 1: Spoken "Matrix" Activation
    # ---------------------------------------------------------
    print("\n" + "#" * 80)
    print(">>> STAGE 1: PLEASE SAY 'MATRIX' INTO YOUR MICROPHONE NOW (7 seconds)")
    print("#" * 80)
    wake_word_detector.start_listening()
    start = time.time()
    detected = None

    with sd.InputStream(samplerate=sr, channels=1, dtype='int16', device=in_dev, blocksize=chunk_size) as stream:
        while (time.time() - start) < 7.0:
            frame, _ = stream.read(chunk_size)
            word = wake_word_detector.process_audio_frame(frame[:, 0], is_tts_speaking=False)
            if word and "matrix" in word.lower():
                detected = word
                print(f"\n[SUCCESS] Spoken wake word DETECTED: '{word.upper()}'!")
                break
            # print progress bar
            rem = 7.0 - (time.time() - start)
            sys.stdout.write(f"\rListening... {rem:.1f}s remaining | Pred: {wake_word_detector.last_predictions}")
            sys.stdout.flush()
            await asyncio.sleep(0.01)

    if not detected:
        print(f"\n[INFO] 'Matrix' not detected within 7s window.")

    # ---------------------------------------------------------
    # STAGE 2: Spoken "Snap" Activation
    # ---------------------------------------------------------
    print("\n\n" + "#" * 80)
    print(">>> STAGE 2: PLEASE SAY 'SNAP' INTO YOUR MICROPHONE NOW (7 seconds)")
    print("#" * 80)
    start = time.time()
    detected_snap_word = None

    with sd.InputStream(samplerate=sr, channels=1, dtype='int16', device=in_dev, blocksize=chunk_size) as stream:
        while (time.time() - start) < 7.0:
            frame, _ = stream.read(chunk_size)
            word = wake_word_detector.process_audio_frame(frame[:, 0], is_tts_speaking=False)
            if word and "snap" in word.lower():
                detected_snap_word = word
                print(f"\n[SUCCESS] Spoken wake word DETECTED: '{word.upper()}'!")
                break
            rem = 7.0 - (time.time() - start)
            sys.stdout.write(f"\rListening... {rem:.1f}s remaining | Pred: {wake_word_detector.last_predictions}")
            sys.stdout.flush()
            await asyncio.sleep(0.01)

    if not detected_snap_word:
        print(f"\n[INFO] 'Snap' not detected within 7s window.")

    # ---------------------------------------------------------
    # STAGE 3: Physical Finger-Snap Detection
    # ---------------------------------------------------------
    print("\n\n" + "#" * 80)
    print(">>> STAGE 3: PLEASE SNAP YOUR FINGERS NEAR THE LAPTOP (7 seconds)")
    print("#" * 80)
    start = time.time()
    detected_physical_snap = False

    with sd.InputStream(samplerate=sr, channels=1, dtype='int16', device=in_dev, blocksize=chunk_size) as stream:
        while (time.time() - start) < 7.0:
            frame, _ = stream.read(chunk_size)
            if snap_detector.process_audio_frame(frame[:, 0], is_tts_speaking=False):
                detected_physical_snap = True
                print(f"\n[SUCCESS] Physical finger snap DETECTED! Metrics: {snap_detector.last_metrics}")
                break
            rem = 7.0 - (time.time() - start)
            sys.stdout.write(f"\rListening... {rem:.1f}s remaining | Peak: {snap_detector.last_metrics.get('peak', 0)}")
            sys.stdout.flush()
            await asyncio.sleep(0.01)

    if not detected_physical_snap:
        print(f"\n[INFO] Finger snap not detected within 7s window.")

    # ---------------------------------------------------------
    # STAGE 4: Speak a Command in English, Hindi, or Hinglish
    # ---------------------------------------------------------
    print("\n\n" + "#" * 80)
    print(">>> STAGE 4: SPEAK A COMMAND (English, Hindi, or Hinglish) (5 seconds recording)")
    print("#" * 80)
    print("[*] Recording speech...")
    raw = sd.rec(int(5.0 * sr), samplerate=sr, channels=1, dtype='int16', device=in_dev)
    sd.wait()
    
    import scipy.io.wavfile as wavfile
    tmp_wav = PROJECT_ROOT / "docs" / "interactive_user_speech.wav"
    wavfile.write(str(tmp_wav), sr, raw[:, 0])

    print("[*] Transcribing speech with faster-whisper INT8...")
    stt_res = await stt_engine.transcribe(tmp_wav)
    user_text = stt_res.get("text", "").strip()
    detected_lang = stt_res.get("detected_language", "en")
    print(f"[+] Recognized: '{user_text}' (Language: {detected_lang})")

    if user_text:
        print("\n[*] Processing command through MatrixBrain...")
        brain_res = await brain.process_user_request(session_id="sess_interactive_user", user_prompt=user_text)
        reply = brain_res.get("response", "")
        print(f"[+] MATRIX Answer: {reply}")

        print("\n[*] Speaking response through laptop speakers...")
        await tts_engine.speak(reply[:250], play_audio=True)
        print("[+] Speech playback complete. Automatic listening resumed!")

    print("\n" + "=" * 80)
    print("Interactive physical acceptance complete.")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(interactive_test())
