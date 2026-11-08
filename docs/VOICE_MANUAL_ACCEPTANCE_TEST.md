# MATRIX Hands-Free Voice Manual Acceptance Testing Guide

**Purpose**: Guide for the user to physically verify the live microphone, wake-word spotting, acoustic barge-in, and speaker response on the host Windows 11 machine.  
**Classification**: `MANUAL USER VERIFICATION PROTOCOL`  

---

## Pre-requisites

1. Ensure your physical microphone is set as the Windows default recording device:
   - *Windows Settings -> System -> Sound -> Input -> Choose your input device*.
2. Ensure speakers or headphones are set as the default output device and volume is audible (~30-50%).
3. Launch MATRIX in PowerShell:
   ```powershell
   cd "C:\Users\Ali Raza Zaidi\Desktop\matrix"
   python run_matrix.py
   ```
   *(Wait until the console displays: `Persistent background native microphone listener service started.`)*

---

## Test Procedure 1: Wake-Word Activation ("Matrix" / "Snap")

1. **Step**: Stand or sit naturally 1 to 3 feet from your laptop/microphone.
2. **Action**: Say clearly: **"Matrix"** (or **"Snap"**).
3. **Expected Result**:
   - The HUD hologram transitions immediately from steady cyan (`IDLE`) to a rapid pulse (`WAKE_DETECTED`), then expands to vivid emerald green (`LISTENING`).
   - Console logs: `ACTIVATING HANDS-FREE on wake-word: 'matrix'`.

---

## Test Procedure 2: Complete Voice Query Cycle

1. **Action**: Immediately speak a command without pressing any keys:  
   *"Matrix, check my computer performance."*
2. **Expected Result**:
   - As you speak, the green orb pulses.
   - When you stop speaking for ~1 second, Silero VAD detects end-of-speech.
   - Faster-Whisper transcribes your voice (Hologram turns royal purple / amber for `THINKING` and `EXECUTING`).
   - MATRIX answers out loud through your speakers in JARVIS's voice (`en-US-ChristopherNeural`):  
     *"Telemetry nominal: CPU is at 12%, RAM utilization is at 82%, with all 16 threads operational."*

---

## Test Procedure 3: Continuous Conversation & Auto-Resumption

1. **Action**: Say: *"Matrix, continue listening after answering."*
2. **Expected Result**:
   - MATRIX acknowledges: *"Continuous hands-free listening is enabled, sir."*
   - Once speech completes, the microphone automatically re-arms into `LISTENING` mode without needing another wake word.
3. **Follow-up**: Say: *"What time is it?"* or *"Open my browser."*
4. **Expected Result**: MATRIX responds directly to the follow-up request.

---

## Test Procedure 4: Barge-In Interruption

1. **Action**: Ask MATRIX a long question: *"Matrix, explain the complete architecture of your 16 specialized agents."*
2. **Action**: While MATRIX is actively speaking through your speakers, speak firmly: **"Matrix, stop!"**
3. **Expected Result**:
   - Audio playback halts instantly within **50 milliseconds**.
   - The hologram flashes red (`INTERRUPTED`) and returns to standby.

---

## Test Procedure 5: Privacy Mode

1. **Action**: In the UI, click the **Mute / Privacy Pause** toggle button (or trigger via API).
2. **Action**: Speak: *"Matrix"* or *"Hello"*.
3. **Expected Result**: Audio ingestion is blocked; no transcription occurs, and no audio buffers are processed.
