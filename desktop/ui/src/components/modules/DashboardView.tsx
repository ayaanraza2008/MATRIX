import React from 'react';
import {
  Mic,
  Square,
  Sparkles,
  Shield,
  Layers,
  Cpu,
  Radio,
  ChevronRight,
} from 'lucide-react';
import { MatrixHologram } from '../hologram/MatrixHologram';
import { HealthData, LiveMetricsData, HologramState, CapabilityItem, HandsFreeMode } from '../../types';

interface DashboardViewProps {
  health: HealthData | null;
  metrics: LiveMetricsData | null;
  hologramState: HologramState;
  capabilities?: CapabilityItem[];
  onQuickAction: (actionText: string) => void;
  lastTranscript?: string;
  lastResponse?: string;
  isSpeaking?: boolean;
  onStopSpeaking?: () => void;
  handsFreeMode?: HandsFreeMode;
  onChangeMode?: (mode: HandsFreeMode) => void;
  onToggleListen?: () => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  health,
  metrics,
  hologramState,
  capabilities: _capabilities = [],
  onQuickAction,
  lastTranscript = '',
  lastResponse = '',
  isSpeaking = false,
  onStopSpeaking,
  handsFreeMode = 'continuous',
  onChangeMode,
  onToggleListen,
}) => {
  void _capabilities;
  const cpuPercent = metrics?.cpu?.percent ?? health?.system?.cpu_percent ?? 0;
  const ramUsed = metrics?.memory?.used_mb ?? health?.system?.ram_used_mb ?? 0;
  const ramTotal = metrics?.memory?.total_mb ?? health?.system?.ram_total_mb ?? 8192;

  // Status message and color based on real backend state
  const getStateMeta = (s: HologramState) => {
    switch (s) {
      case 'wake_word':
        return {
          label: 'WAKE-WORD DETECTED',
          desc: 'Activated by "Matrix" or "Snap". Preparing to listen...',
          badge: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 animate-pulse',
        };
      case 'listening':
        return {
          label: 'LISTENING (HANDS-FREE)',
          desc: 'Speak your directive naturally. End-of-speech will auto-submit.',
          badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 animate-pulse',
        };
      case 'thinking':
        return {
          label: 'NEURAL REASONING',
          desc: 'Local Qwen2.5 GGUF analyzing intent and planning execution...',
          badge: 'bg-purple-500/20 text-purple-300 border-purple-500/40 animate-pulse',
        };
      case 'processing':
        return {
          label: 'PROCESSING DIRECTIVE',
          desc: 'Synthesizing knowledge and formulating multi-step plan...',
          badge: 'bg-blue-500/20 text-blue-300 border-blue-500/40 animate-pulse',
        };
      case 'executing':
        return {
          label: 'EXECUTING MULTI-AGENT TASK',
          desc: 'Autonomous agent grid executing tools under Policy Level 3/4...',
          badge: 'bg-amber-500/20 text-amber-300 border-amber-500/40 animate-pulse',
        };
      case 'speaking':
        return {
          label: 'SPEAKING (CHRISTOPHER NEURAL)',
          desc: 'Streaming natural voice response. Say "Matrix, stop" to interrupt.',
          badge: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 animate-pulse',
        };
      case 'interrupted':
        return {
          label: 'INTERRUPTED',
          desc: 'Speech immediately canceled. Resuming standby...',
          badge: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
        };
      case 'error':
        return {
          label: 'AUDIO SUBSYSTEM ALERT',
          desc: 'Audio device warning. Check microphone permissions.',
          badge: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
        };
      case 'offline':
        return {
          label: 'DISCONNECTED',
          desc: 'Waiting for backend reconnection on port 8000...',
          badge: 'bg-slate-700/40 text-slate-400 border-slate-600/40',
        };
      case 'idle':
      default:
        return {
          label: handsFreeMode === 'privacy_pause' ? 'MICROPHONE PAUSED' : 'WAKE-WORD STANDBY',
          desc:
            handsFreeMode === 'privacy_pause'
              ? 'Privacy mode enabled. Wake-word detection is disarmed.'
              : 'Listening locally for "Matrix" or "Snap". Zero cloud audio upload.',
          badge:
            handsFreeMode === 'privacy_pause'
              ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
              : 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
        };
    }
  };

  const stateMeta = getStateMeta(hologramState);

  const quickPrompts = [
    'Research the best free Python libraries for voice assistants',
    'Inspect my computer and tell me what is consuming memory',
    'Open my browser and search for latest AI developments',
    'Create a Python application with a graphical interface',
    'Summarize my recent files',
  ];

  return (
    <div className="flex-1 overflow-y-auto flex flex-col items-center justify-between p-4 md:p-6 bg-[#030712] text-slate-100 relative select-none">
      {/* Background Subtle Gradient & Grid */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_35%,rgba(0,240,255,0.06),transparent_70%)] pointer-events-none" />
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#081020_1px,transparent_1px),linear-gradient(to_bottom,#081020_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_35%,#000_70%,transparent_100%)] opacity-30 pointer-events-none" />

      {/* Top Bar: Minimal Status & Mode Switcher */}
      <div className="w-full max-w-5xl flex items-center justify-between z-10 pt-1">
        {/* Identity & Status */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                hologramState === 'listening' ? 'bg-emerald-400' :
                hologramState === 'speaking' ? 'bg-cyan-400' :
                hologramState === 'thinking' ? 'bg-purple-400' : 'bg-cyan-400'
              }`} />
              <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                hologramState === 'listening' ? 'bg-emerald-500' :
                hologramState === 'speaking' ? 'bg-cyan-500' :
                hologramState === 'thinking' ? 'bg-purple-500' : 'bg-cyan-500'
              }`} />
            </span>
            <span className="text-xs font-mono tracking-widest uppercase font-semibold text-cyan-400">
              JARVIS MODE
            </span>
          </div>

          <span className="text-xs text-slate-600">|</span>

          {/* Wake Words Supported Pill */}
          <div className="hidden sm:flex items-center gap-1.5 text-[11px] font-mono text-slate-400 bg-slate-900/60 px-2.5 py-1 rounded-full border border-slate-800">
            <Radio className="w-3 h-3 text-cyan-400 animate-pulse" />
            <span>Wake words: <strong className="text-cyan-300">"Matrix"</strong> · <strong className="text-cyan-300">"Snap"</strong></span>
          </div>
        </div>

        {/* Hands-Free Mode Selector */}
        <div className="flex items-center gap-1.5 bg-slate-950/80 p-1 rounded-lg border border-slate-800/80 text-xs font-mono">
          <button
            onClick={() => onChangeMode && onChangeMode('continuous')}
            className={`px-2.5 py-1 rounded transition-colors ${
              handsFreeMode === 'continuous'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold shadow-sm shadow-cyan-500/20'
                : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Continuous conversation: Resumes listening automatically after responding"
          >
            Continuous
          </button>
          <button
            onClick={() => onChangeMode && onChangeMode('wake_word_only')}
            className={`px-2.5 py-1 rounded transition-colors ${
              handsFreeMode === 'wake_word_only'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Wake-word only: Requires saying 'Matrix' or 'Snap' before every turn"
          >
            Wake-Word
          </button>
          <button
            onClick={() => onChangeMode && onChangeMode('privacy_pause')}
            className={`px-2.5 py-1 rounded transition-colors ${
              handsFreeMode === 'privacy_pause'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Privacy mode: Microphones completely disarmed"
          >
            Pause Mic
          </button>
        </div>
      </div>

      {/* Main Central Stage: Large Holographic Core */}
      <div className="relative flex flex-col items-center justify-center my-auto z-10 py-2">
        {/* Hologram Canvas */}
        <div className="relative flex items-center justify-center">
          <MatrixHologram
            state={hologramState}
            size={450}
            className="filter drop-shadow-[0_0_40px_rgba(0,240,255,0.25)]"
            onClick={onToggleListen}
          />

          {/* Center Hologram Touch Prompt */}
          <div className="absolute -bottom-2 text-center pointer-events-none">
            <span className={`text-[10px] font-mono uppercase tracking-widest px-3 py-1 rounded-full border ${stateMeta.badge}`}>
              {stateMeta.label}
            </span>
          </div>
        </div>

        {/* State Description */}
        <p className="text-xs font-mono text-slate-400 text-center mt-4 max-w-md">
          {stateMeta.desc}
        </p>

        {/* Stop Speaking / Interruption Button */}
        {isSpeaking && onStopSpeaking && (
          <button
            onClick={onStopSpeaking}
            className="mt-3 flex items-center gap-2 px-4 py-1.5 rounded-full bg-rose-600/30 hover:bg-rose-600/50 text-rose-300 border border-rose-500/50 text-xs font-mono tracking-wider font-semibold animate-pulse transition-all shadow-lg shadow-rose-950"
          >
            <Square className="w-3.5 h-3.5 fill-rose-400" />
            STOP SPEAKING (INTERRUPT)
          </button>
        )}

        {/* Floating Speech HUD (Live Transcripts & JARVIS Answers) */}
        {(lastTranscript || lastResponse) && (
          <div className="w-full max-w-2xl mt-5 space-y-2.5 z-20">
            {lastTranscript && (
              <div className="bg-slate-900/60 backdrop-blur-md rounded-xl p-3 border border-slate-800/80 shadow-xl flex items-start gap-2.5">
                <Mic className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div className="text-[10px] font-mono uppercase text-cyan-400 tracking-wider">User Directive</div>
                  <div className="text-sm font-medium text-slate-100 mt-0.5">"{lastTranscript}"</div>
                </div>
              </div>
            )}

            {lastResponse && (
              <div className="bg-slate-950/80 backdrop-blur-md rounded-xl p-3.5 border border-cyan-500/30 shadow-2xl shadow-cyan-950/20 flex items-start gap-2.5">
                <Sparkles className="w-4 h-4 text-cyan-300 shrink-0 mt-0.5 animate-pulse" />
                <div className="flex-1">
                  <div className="text-[10px] font-mono uppercase text-cyan-300 tracking-wider flex items-center justify-between">
                    <span>MATRIX Spoken Response</span>
                    <span className="text-slate-500">Offline Qwen2.5</span>
                  </div>
                  <div className="text-sm text-slate-200 leading-relaxed mt-1 line-clamp-4">
                    {lastResponse}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Bottom Bar: Quick Directives & System Vitals */}
      <div className="w-full max-w-4xl flex flex-col items-center gap-3 z-10 pb-1">
        {/* Quick Suggestion Pills */}
        <div className="flex flex-wrap items-center justify-center gap-2">
          {quickPrompts.slice(0, 3).map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => onQuickAction(prompt)}
              className="flex items-center gap-1.5 text-[11px] font-mono text-slate-400 hover:text-cyan-300 bg-slate-900/60 hover:bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-800/80 hover:border-cyan-500/40 transition-all duration-200"
            >
              <span>{prompt}</span>
              <ChevronRight className="w-3 h-3 opacity-60" />
            </button>
          ))}
        </div>

        {/* Minimal Vitals Footprint */}
        <div className="flex items-center gap-4 text-[10px] font-mono text-slate-500">
          <span className="flex items-center gap-1">
            <Cpu className="w-3 h-3 text-cyan-400" />
            Ryzen 7 5700U ({cpuPercent}%)
          </span>
          <span>·</span>
          <span className="flex items-center gap-1">
            <Layers className="w-3 h-3 text-blue-400" />
            RAM: {(ramUsed / 1024).toFixed(1)} / {(ramTotal / 1024).toFixed(1)} GB
          </span>
          <span>·</span>
          <span className="flex items-center gap-1">
            <Shield className="w-3 h-3 text-emerald-400" />
            Policy Level 3/4 Active
          </span>
        </div>
      </div>
    </div>
  );
};
