import React, { useState, useEffect, useRef } from 'react';
import {
  Hand,
  Eye,
  Rotate3d,
  MousePointer,
  RefreshCw,
  Target,
  Sparkles,
  Zap,
  Activity,
  Sliders
} from 'lucide-react';

interface TelemetryData {
  mode: string;
  active: boolean;
  fps: number;
  latency_ms: number;
  gesture_3d?: {
    rotation_deg: { yaw: number; pitch: number };
    delta: { dx: number; dy: number };
    css_transform: string;
    is_jumping: boolean;
    rotation_count: number;
  };
  gesture_scroll?: {
    scroll_units: number;
    velocity: number;
    direction: string;
    is_locked: boolean;
    active_gesture: string;
    speed_setting: string;
    total_scrolled: number;
  };
  eye?: {
    face_detected: boolean;
    confidence: number;
    ear?: { left: number; right: number; average: number };
    blink?: { is_blinking: boolean; event: string; total_blinks: number };
    gaze?: { direction: string; screen_x: number; screen_y: number; pixel_x: number; pixel_y: number };
    dwell?: { progress: number; clicked: boolean };
    head_pose?: { yaw_deg: number; pitch_deg: number; roll_deg: number };
    calibration?: { active: boolean; current_step: string; is_calibrated: boolean };
  };
  hands?: {
    hands_detected: number;
    hands: Array<{
      hand_id: number;
      handedness: string;
      gesture: string;
      open_finger_count: number;
      centroid: { x: number; y: number };
    }>;
  };
  scene_summary?: string;
}

export const AirTouchStudio: React.FC = () => {
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
  const [mode, setMode] = useState<string>('GESTURE_3D');
  const [sensitivity3d, setSensitivity3d] = useState<number>(3.5);
  const [scrollSpeed, setScrollSpeed] = useState<string>('MEDIUM');
  const [vqaQuery, setVqaQuery] = useState<string>('Matrix, what am I looking at?');
  const [vqaResponse, setVqaResponse] = useState<string | null>(null);
  const [vqaLoading, setVqaLoading] = useState<boolean>(false);
  const [calibrationStep, setCalibrationStep] = useState<string>('IDLE');
  const scrollRef = useRef<HTMLDivElement>(null);

  // Poll telemetry every 80ms
  useEffect(() => {
    let isMounted = true;
    const interval = setInterval(async () => {
      try {
        const res = await fetch('/api/v1/airtouch/telemetry');
        if (res.ok && isMounted) {
          const data: TelemetryData = await res.json();
          setTelemetry(data);

          // Auto-scroll the scroll test area if gesture scroll units arrive
          if (data.gesture_scroll && data.gesture_scroll.scroll_units !== 0 && scrollRef.current) {
            scrollRef.current.scrollTop -= data.gesture_scroll.scroll_units * 3;
          }
        }
      } catch {
        // Silently handle polling disconnect
      }
    }, 80);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleSetMode = async (newMode: string) => {
    setMode(newMode);
    try {
      await fetch('/api/v1/airtouch/mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: newMode })
      });
    } catch (e) {
      console.error('Failed to set mode:', e);
    }
  };

  const handleReset3D = async () => {
    try {
      await fetch('/api/v1/airtouch/reset_3d', { method: 'POST' });
    } catch (e) {
      console.error('Failed to reset 3D:', e);
    }
  };

  const handleSensitivityChange = async (val: number) => {
    setSensitivity3d(val);
    try {
      await fetch('/api/v1/airtouch/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sensitivity_3d: val })
      });
    } catch (e) {
      console.error('Failed to set 3d sensitivity:', e);
    }
  };

  const handleCalibrate = async () => {
    try {
      const res = await fetch('/api/v1/airtouch/calibrate', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setCalibrationStep(data.target || 'NEXT');
      }
    } catch (e) {
      console.error('Calibration trigger failed:', e);
    }
  };

  const handleSpeedChange = async (speed: string) => {
    setScrollSpeed(speed);
    try {
      await fetch('/api/v1/airtouch/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scroll_speed: speed })
      });
    } catch (e) {
      console.error('Failed to set scroll speed:', e);
    }
  };

  const handleVQA = async () => {
    if (!vqaQuery) return;
    setVqaLoading(true);
    setVqaResponse(null);
    try {
      const res = await fetch('/api/v1/airtouch/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: vqaQuery })
      });
      if (res.ok) {
        const data = await res.json();
        setVqaResponse(data.response);
      }
    } catch {
      setVqaResponse('Unable to reach vision query service.');
    } finally {
      setVqaLoading(false);
    }
  };

  const g3d = telemetry?.gesture_3d;
  const gScroll = telemetry?.gesture_scroll;
  const gEye = telemetry?.eye;
  const hands = telemetry?.hands?.hands || [];

  return (
    <div className="space-y-6">
      {/* Header & Mode Bar */}
      <div className="matrix-glass rounded-xl p-4 border border-matrix-cyan/30 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-matrix-cyan/15 text-matrix-cyan border border-matrix-cyan/40">
            <Hand className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h2 className="text-sm font-mono font-bold uppercase text-slate-100 flex items-center gap-2">
              AIRTOUCH VISION & GESTURE STUDIO
              <span className="text-[10px] px-2 py-0.5 rounded bg-matrix-cyan/20 text-matrix-cyan border border-matrix-cyan/40">
                PROD v2.0
              </span>
            </h2>
            <p className="text-xs font-mono text-slate-400">
              Gesture3D Hologram · Touchless Scroll · GesturEye Tracking · Multi-modal VQA
            </p>
          </div>
        </div>

        {/* Operating Mode Buttons */}
        <div className="flex items-center gap-1 bg-slate-900/90 p-1 rounded-lg border border-slate-800">
          {['OFF', 'GESTURE_3D', 'GESTURE_SCROLL', 'GESTURE_EYE', 'FULL_VISION'].map((m) => (
            <button
              key={m}
              onClick={() => handleSetMode(m)}
              className={`px-2.5 py-1 text-[11px] font-mono font-bold rounded transition-all ${
                mode === m
                  ? 'bg-matrix-cyan text-slate-950 shadow-lg shadow-matrix-cyan/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              {m.replace('_', ' ')}
            </button>
          ))}
        </div>

        {/* Live FPS & Latency */}
        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="flex items-center gap-1.5 text-matrix-green">
            <Activity className="w-3.5 h-3.5" />
            <span>{telemetry?.fps || 0} FPS</span>
          </div>
          <div className="text-slate-400">
            Latency: <span className="text-matrix-cyan">{telemetry?.latency_ms || 0}ms</span>
          </div>
        </div>
      </div>

      {/* Main Studio Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Module 1: Gesture3D Interactive Hologram Canvas */}
        <div className="matrix-glass rounded-xl p-5 border border-slate-800 space-y-4 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-mono font-bold uppercase text-slate-200 flex items-center gap-2">
              <Rotate3d className="w-4 h-4 text-matrix-cyan" />
              GESTURE 3D HOLOGRAM
            </h3>
            <button
              onClick={handleReset3D}
              className="text-[11px] font-mono text-slate-400 hover:text-matrix-cyan flex items-center gap-1 bg-slate-900/80 px-2 py-1 rounded border border-slate-800"
            >
              <RefreshCw className="w-3 h-3" /> RESET
            </button>
          </div>

          {/* Interactive CSS 3D Hologram Box */}
          <div className="h-56 bg-slate-950/90 rounded-lg border border-matrix-cyan/20 flex items-center justify-center overflow-hidden relative" style={{ perspective: '800px' }}>
            <div
              className="w-24 h-24 border-2 border-matrix-cyan/60 rounded-xl relative transition-transform duration-75 flex items-center justify-center shadow-lg shadow-matrix-cyan/20"
              style={{
                transformStyle: 'preserve-3d',
                transform: g3d?.css_transform || 'rotateY(0deg) rotateX(0deg)',
              }}
            >
              <div className="absolute inset-0 border border-matrix-cyan/40 rounded-xl bg-matrix-cyan/10 flex items-center justify-center font-mono text-[10px] text-matrix-cyan">
                JARVIS HUD
              </div>
              <div
                className="absolute inset-0 border border-cyan-400/30 rounded-xl"
                style={{ transform: 'translateZ(30px)' }}
              />
              <div
                className="absolute inset-0 border border-blue-400/30 rounded-xl"
                style={{ transform: 'translateZ(-30px)' }}
              />
              <Sparkles className="w-6 h-6 text-matrix-cyan animate-pulse" />
            </div>

            {/* Rotational degree telemetry */}
            <div className="absolute bottom-2 left-2 text-[10px] font-mono text-slate-400 bg-slate-950/80 px-2 py-0.5 rounded border border-slate-800">
              Yaw: <span className="text-matrix-cyan">{g3d?.rotation_deg?.yaw || 0}°</span> · Pitch:{' '}
              <span className="text-matrix-cyan">{g3d?.rotation_deg?.pitch || 0}°</span>
            </div>
            {g3d?.is_jumping && (
              <div className="absolute top-2 right-2 text-[10px] font-mono text-matrix-red bg-slate-950/90 px-2 py-0.5 rounded border border-matrix-red/40">
                JUMP SUPPRESSED
              </div>
            )}
          </div>

          {/* Sensitivity Slider & Hand tracking state */}
          <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80 text-xs font-mono space-y-2">
            <div className="flex items-center justify-between text-slate-300">
              <span className="flex items-center gap-1.5"><Sliders className="w-3 h-3 text-matrix-cyan" /> Sensitivity:</span>
              <span className="text-matrix-cyan font-bold">{sensitivity3d}x</span>
            </div>
            <input
              type="range"
              min="1.0"
              max="8.0"
              step="0.5"
              value={sensitivity3d}
              onChange={(e) => handleSensitivityChange(parseFloat(e.target.value))}
              className="w-full accent-cyan-400 h-1 bg-slate-800 rounded-lg cursor-pointer"
            />
            {hands.length > 0 && (
              <div className="flex justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-900">
                <span>Gesture: <span className="text-matrix-green">{hands[0].gesture}</span></span>
                <span>Fingers: <span className="text-matrix-cyan">{hands[0].open_finger_count}</span></span>
              </div>
            )}
          </div>
        </div>

        {/* Module 2: Touchless Gesture Scroll Simulator */}
        <div className="matrix-glass rounded-xl p-5 border border-slate-800 space-y-4 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-mono font-bold uppercase text-slate-200 flex items-center gap-2">
              <MousePointer className="w-4 h-4 text-matrix-blue" />
              GESTURE SCROLL TESTER
            </h3>
            {/* Speed presets */}
            <div className="flex items-center gap-1 bg-slate-900 p-0.5 rounded border border-slate-800">
              {['LOW', 'MEDIUM', 'HIGH'].map((spd) => (
                <button
                  key={spd}
                  onClick={() => handleSpeedChange(spd)}
                  className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${
                    scrollSpeed === spd
                      ? 'bg-matrix-blue text-slate-950 font-bold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {spd}
                </button>
              ))}
            </div>
          </div>

          {/* Simulated scroll container */}
          <div
            ref={scrollRef}
            className="h-56 bg-slate-950/90 rounded-lg border border-slate-800 p-3 overflow-y-auto space-y-2 font-mono text-xs text-slate-300 relative scroll-smooth"
          >
            <div className="text-[10px] text-matrix-cyan font-bold sticky top-0 bg-slate-950/90 py-1 border-b border-slate-800">
              DOCUMENT SIMULATOR · AIRTOUCH GESTURE SCROLL
            </div>
            <p className="text-[11px] text-slate-400">
              1. Open palm and move hand up/down to scroll this document naturally.
            </p>
            <p className="text-[11px] text-slate-400">
              2. Close your hand into a fist to stop and lock the scroll position.
            </p>
            <div className="p-2 rounded bg-slate-900 border border-slate-800 text-[10px] text-slate-300">
              <code>// MATRIX CORE ORCHESTRATOR TELEMETRY PIPELINE</code>
              <br />
              <code>const engine = AirTouchGestureScroll.initialize();</code>
              <br />
              <code>engine.setSensitivity(1.0);</code>
              <br />
              <code>engine.enableOSScroll(true);</code>
            </div>
            {Array.from({ length: 15 }).map((_, i) => (
              <div key={i} className="text-[10px] text-slate-500 py-0.5 border-b border-slate-900">
                [Telemetry Log Entry {i + 1}] Hand vector velocity validated · Accidental scroll suppressed.
              </div>
            ))}
          </div>

          {/* Scroll telemetry banner */}
          <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80 text-xs font-mono flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="text-slate-400 text-[11px]">Direction: <span className="text-matrix-cyan font-bold">{gScroll?.direction || 'IDLE'}</span></div>
              <div className="text-slate-400 text-[11px]">Velocity: <span className="text-matrix-green">{gScroll?.velocity || 0}</span></div>
            </div>
            <div className="text-right">
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                  gScroll?.is_locked
                    ? 'bg-matrix-red/15 text-matrix-red border-matrix-red/40'
                    : 'bg-matrix-green/15 text-matrix-green border-matrix-green/40'
                }`}
              >
                {gScroll?.is_locked ? 'FIST LOCKED' : 'UNLOCKED'}
              </span>
            </div>
          </div>
        </div>

        {/* Module 3: GesturEye Eye Tracking & Calibration */}
        <div className="matrix-glass rounded-xl p-5 border border-slate-800 space-y-4 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-mono font-bold uppercase text-slate-200 flex items-center gap-2">
              <Eye className="w-4 h-4 text-matrix-cyan" />
              GESTUREYE TRACKING & DWELL
            </h3>
            <button
              onClick={handleCalibrate}
              className="text-[11px] font-mono text-matrix-cyan hover:bg-matrix-cyan/20 flex items-center gap-1 bg-matrix-cyan/10 px-2 py-1 rounded border border-matrix-cyan/40"
            >
              <Target className="w-3 h-3" /> CALIBRATE
            </button>
          </div>

          {/* Eye Reticle & Gaze Visualizer */}
          <div className="h-56 bg-slate-950/90 rounded-lg border border-slate-800 relative overflow-hidden flex items-center justify-center">
            {/* Normalized Screen Reticle */}
            <div
              className="absolute w-8 h-8 rounded-full border-2 border-matrix-cyan bg-matrix-cyan/20 flex items-center justify-center transition-all duration-75 shadow-lg shadow-matrix-cyan/30"
              style={{
                left: `${Math.min(92, Math.max(8, (gEye?.gaze?.screen_x || 0.5) * 100))}%`,
                top: `${Math.min(92, Math.max(8, (gEye?.gaze?.screen_y || 0.5) * 100))}%`,
                transform: 'translate(-50%, -50%)',
              }}
            >
              <div className="w-2 h-2 rounded-full bg-matrix-red" />
            </div>

            {/* Dwell Progress Indicator */}
            {gEye?.dwell && gEye.dwell.progress > 0 && (
              <div className="absolute top-2 left-2 text-[10px] font-mono text-matrix-green bg-slate-950/90 px-2 py-0.5 rounded border border-matrix-green/40">
                Dwell Click: {Math.round(gEye.dwell.progress * 100)}%
              </div>
            )}

            {/* Calibration Target Step */}
            {calibrationStep !== 'IDLE' && (
              <div className="absolute top-2 left-2 text-[10px] font-mono text-matrix-cyan bg-slate-950/90 px-2 py-0.5 rounded border border-matrix-cyan/40 animate-pulse">
                Target: {calibrationStep}
              </div>
            )}

            {/* Gaze Direction Banner */}
            <div className="absolute bottom-2 right-2 text-[10px] font-mono text-slate-300 bg-slate-950/90 px-2 py-0.5 rounded border border-slate-800">
              Gaze: <span className="text-matrix-cyan font-bold">{gEye?.gaze?.direction || 'CENTER'}</span>
            </div>

            {/* Face Status */}
            <div className="absolute top-2 right-2 text-[10px] font-mono">
              <span
                className={`px-2 py-0.5 rounded border ${
                  gEye?.face_detected
                    ? 'bg-matrix-green/15 text-matrix-green border-matrix-green/40'
                    : 'bg-matrix-red/15 text-matrix-red border-matrix-red/40'
                }`}
              >
                {gEye?.face_detected ? 'FACE DETECTED' : 'NO FACE'}
              </span>
            </div>
          </div>

          {/* Eye Metrics Details */}
          <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80 text-xs font-mono space-y-1">
            <div className="flex justify-between text-slate-300">
              <span>Blink State:</span>
              <span className="text-matrix-cyan">
                {gEye?.blink?.is_blinking ? 'BLINKING' : 'OPEN'}{' '}
                <span className="text-slate-500">({gEye?.blink?.total_blinks || 0} blinks)</span>
              </span>
            </div>
            <div className="flex justify-between text-[11px] text-slate-400">
              <span>EAR: {gEye?.ear?.average || 0.0}</span>
              <span>Head Yaw: {gEye?.head_pose?.yaw_deg || 0}°</span>
            </div>
          </div>
        </div>
      </div>

      {/* Visual Question Answering (VQA) Bar */}
      <div className="matrix-glass rounded-xl p-4 border border-slate-800 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-mono font-bold uppercase text-slate-200 flex items-center gap-2">
            <Zap className="w-4 h-4 text-matrix-cyan" />
            VISUAL INTELLIGENCE & NATURAL QUERY ("MATRIX, WHAT AM I LOOKING AT?")
          </h3>
          <span className="text-[10px] font-mono text-slate-400">
            Powered by ModernAIVisionSubsystem + OCR
          </span>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="text"
            value={vqaQuery}
            onChange={(e) => setVqaQuery(e.target.value)}
            placeholder="Ask a visual query (e.g. 'Matrix, what am I looking at?')"
            className="flex-1 bg-slate-950/90 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-matrix-cyan"
          />
          <button
            onClick={handleVQA}
            disabled={vqaLoading}
            className="px-4 py-2 rounded-lg bg-matrix-cyan text-slate-950 font-mono font-bold text-xs hover:bg-cyan-300 disabled:opacity-40 transition-colors flex items-center gap-1.5"
          >
            {vqaLoading ? 'ANALYZING...' : 'ASK MATRIX'}
          </button>
        </div>

        {vqaResponse && (
          <div className="p-3 rounded-lg bg-slate-950/90 border border-matrix-cyan/40 text-xs font-mono text-matrix-cyan space-y-1">
            <div className="text-[10px] text-slate-400 uppercase font-bold">Matrix Visual Perception:</div>
            <div>{vqaResponse}</div>
          </div>
        )}
      </div>
    </div>
  );
};
