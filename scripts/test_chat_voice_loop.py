"""Verify complete Voice Loop: Speech -> STT -> Brain -> TTS -> Audio."""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from voice.text_to_speech.engine import tts_engine
from voice.speech_to_text.engine import stt_engine
from core.brain import brain

async def test():
    print("=" * 60)
    print("TESTING FULL END-TO-END VOICE LOOP")
    print("=" * 60)
    
    # 1. Synthesize a user test phrase
    user_phrase = "Hello MATRIX, how are you today?"
    print(f"[1] Simulating user speech: '{user_phrase}'")
    user_audio = await tts_engine.speak(user_phrase)
    assert user_audio and user_audio.exists()
    
    # 2. Transcribe using faster-whisper
    stt_res = await stt_engine.transcribe(user_audio)
    transcribed = stt_res.get("text", "").strip()
    print(f"[2] Whisper Transcribed: '{transcribed}'")
    assert len(transcribed) > 0
    
    # 3. Process via MATRIX Brain
    brain_res = await brain.process_user_request("sess_voice_e2e", transcribed)
    reply = brain_res.get("response", "")
    print(f"[3] Brain AI Response: '{reply}'")
    assert len(reply) > 5
    
    # 4. Synthesize AI reply back to speech
    ai_audio = await tts_engine.speak(reply)
    print(f"[4] AI Response Synthesized to Audio: {ai_audio.name} ({ai_audio.stat().st_size} bytes)")
    assert ai_audio and ai_audio.exists() and ai_audio.stat().st_size > 0
    
    print("\n[+] FULL VOICE LOOP (SPEECH -> STT -> BRAIN -> TTS) PASSED 100%!")

if __name__ == "__main__":
    asyncio.run(test())
