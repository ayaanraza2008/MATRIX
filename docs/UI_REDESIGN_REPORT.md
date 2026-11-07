# MATRIX Front Page & Minimal Holographic UI Redesign Report

## 1. Design Overview

The MATRIX front page has been completely redesigned into a clean, minimal, futuristic HUD inspired by Iron Man's JARVIS. Crowded metric cards and cluttered tables have been removed from the main landing screen and organized into a collapsible navigation dock, making the **Large Central Hologram Core** the undisputed visual anchor of the ecosystem.

---

## 2. Visual Identity & Aesthetic Principles

- **Deep Black Canvas**: Pure black background (`#030712`) with subtle radial gradients and low-opacity cybernetic coordinate grids.
- **Color Accents**: Electric cyan (`#00f0ff`), deep azure (`#0066ff`), emerald listening rings (`#00ff9d`), royal violet thinking vortices (`#9933ff`), and amber execution glows (`#f59e0b`).
- **Depth & Atmosphere**: Triple-layered Three.js visual composition featuring an internal rotating wireframe icosahedron, a dense 1000-particle spherical cloud, 4 gyroscopic concentric orbital rings, and an ambient floating dust field.
- **Performance Budget**: Built using WebGL with additive blending and `low-power` renderer preferences, sustaining a smooth 60fps on integrated AMD Radeon graphics with negligible power draw.

---

## 3. Real Backend-Driven Visual States

The central hologram dynamically transitions between 10 visual states driven by live backend WebSocket events:

| Visual State | Color Palette | Animation Dynamics | Backend Trigger |
| :--- | :--- | :--- | :--- |
| **IDLE** | Electric Cyan & Deep Blue | Slow serene breathing wave | Standby mode listening for "Matrix" or "Snap" |
| **WAKE_WORD** | Intense Cyan & White | High-speed electric activation burst | Wake-word detected by openWakeWord |
| **LISTENING** | Neon Emerald & Cyan | Concentric acoustic radar pulse rings | Silero VAD actively capturing speech frames |
| **THINKING** | Royal Violet & Azure | Internal swirling neural vortex | Local Qwen2.5 GGUF LLM generating thoughts |
| **PROCESSING** | Cyan & Indigo | High-speed orbital particle spin | Tool parameter extraction & plan formulation |
| **EXECUTING** | Amber & Cyan | Rotating arc segments & purposeful bursts | Multi-agent tool execution across agent grid |
| **SPEAKING** | Cyan & Blue Pulse | Audio-synchronized undulating waveform | Edge-TTS neural speech audio playback |
| **INTERRUPTED** | Rose Crimson | Immediate sharp transition & red pulse | User said "Matrix, stop" or clicked Stop button |
| **ERROR** | Crimson & Dark Burgundy | Disturbed, erratic particle drift | Audio device or permission failure |
| **OFFLINE** | Dim Slate Gray | Faint slow drift | Backend disconnected on port 8000 |

---

## 4. Minimal Layout Hierarchy

```text
┌────────────────────────────────────────────────────────────────────────┐
│  [●] JARVIS MODE   |  Wake words: "Matrix" · "Snap"    [Mode Selector] │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│                                                                        │
│                           ╭───────────────╮                            │
│                           │               │                            │
│                           │    CENTRAL    │                            │
│                           │   HOLOGRAM    │                            │
│                           │    CORE       │                            │
│                           │   (450px)     │                            │
│                           │               │                            │
│                           ╰───────────────╯                            │
│                                                                        │
│                    [ WAKE-WORD STANDBY: "MATRIX" / "SNAP" ]            │
│                 "Listening locally. Zero cloud audio upload."          │
│                                                                        │
│          ┌───────────────────────────────────────────────────┐         │
│          │ [Mic] User Directive: "..."                       │         │
│          │ [AI]  MATRIX Spoken Response: "..."               │         │
│          └───────────────────────────────────────────────────┘         │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│  [Research Voice Libs]  [Inspect Memory]  [Summarize PDF]              │
│  Ryzen 7 5700U · RAM: 2.1 / 8.0 GB · Policy Level 3/4 Active           │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Voice-First Controls & Interactivity

1. **Direct Touch Activation**: Clicking the large central hologram acts as a tactile toggle to arm or disarm active listening.
2. **Floating Speech HUD**: Smoothly animates into view when a user directive is recognized, showing the transcribed prompt and the spoken AI response.
3. **Interrupt Button**: An animated red **STOP SPEAKING** button appears during audio playback, allowing one-click cancellation.
4. **Mode Selector**: Top-right switcher allows seamless switching between **Continuous**, **Wake-Word Only**, and **Pause Mic** (privacy mode).
5. **Clean Navigation Dock**: The left sidebar collapses cleanly into a slim icon rail, granting immediate 1-click access to the full matrix of specialized agents, files, research, system monitoring, and developer studio without cluttering the JARVIS front screen.
