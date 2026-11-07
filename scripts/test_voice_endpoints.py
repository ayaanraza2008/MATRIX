import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
sys.stdout.reconfigure(encoding='utf-8')

from voice.text_to_speech.engine import tts_engine
from voice.wake_word.engine import wake_word_detector
from voice.speech_to_text.engine import stt_engine

async def main():
    print("=== TESTING ENHANCED VOICE SUBSYSTEM ===")

    # 1. English JARVIS Speech
    print("1. Synthesizing English Speech...")
    p1 = await tts_engine.speak("All MATRIX systems are fully functional, Sir.")
    assert p1 and p1.exists()
    print(f"  English Audio Generated: {p1.name} ({p1.stat().st_size} bytes)")

    # 2. Hindi / Hinglish Speech
    print("2. Synthesizing Hinglish Speech...")
    p2 = await tts_engine.speak("Namaste, main MATRIX hoon. Aapki kya madad kar sakta hoon?")
    assert p2 and p2.exists()
    print(f"  Hinglish Audio Generated: {p2.name} ({p2.stat().st_size} bytes)")

    # 3. Transcribe speech using faster-whisper
    print("3. Transcribing generated speech...")
    trans = await stt_engine.transcribe(p1)
    print(f"  Transcribed Text: '{trans.get('text')}' (Language: {trans.get('detected_language')})")
    assert "matrix" in trans.get("text", "").lower()

    # 4. Wake word toggle
    print("4. Testing wake-word toggle...")
    wake_word_detector.start_listening()
    assert wake_word_detector.is_listening is True
    wake_word_detector.stop_listening()
    assert wake_word_detector.is_listening is False
    print("  Wake-word toggle operational.")

    print("\nSUCCESS: ALL VOICE & JARVIS INTERACTIONS VERIFIED!")

asyncio.run(main())
