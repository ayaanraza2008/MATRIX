import React from 'react';
import {
  Wifi,
  WifiOff,
  Cpu,
  Layers,
  Sparkles,
  Volume2,
  VolumeX,
  Radio,
  Clock,
} from 'lucide-react';
import { HealthData, LiveMetricsData } from '../../types';

interface TopNavbarProps {
  connected: boolean;
  health: HealthData | null;
  metrics: LiveMetricsData | null;
  voiceActive: boolean;
  onToggleVoice: () => void;
  audioMuted: boolean;
  onToggleMute: () => void;
}

export const TopNavbar: React.FC<TopNavbarProps> = ({
  connected,
  health,
  metrics,
  voiceActive,
  onToggleVoice,
  audioMuted,
  onToggleMute,
}) => {
  const cpuPercent = metrics?.cpu?.percent ?? health?.system?.cpu_percent ?? 0;
  const ramPercent = metrics?.memory?.percent ?? health?.system?.ram_percent ?? 0;
  const dbLatency = health?.database?.latency_ms ?? 0;

  return (
    <header className="h-16 px-6 border-b border-matrix-border/60 bg-[#070B16]/80 backdrop-blur-md flex items-center justify-between z-20">
      {/* Left: System Status & Hardware Profile */}
      <div className="flex items-center gap-4">
        {/* Connection Status Pill */}
        <div
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-mono transition-colors ${
            connected
              ? 'bg-matrix-green/10 border-matrix-green/30 text-matrix-green'
              : 'bg-matrix-red/10 border-matrix-red/30 text-matrix-red'
          }`}
        >
          {connected ? (
            <>
              <span className="w-2 h-2 rounded-full bg-matrix-green animate-ping" />
              <Wifi className="w-3.5 h-3.5" />
              <span className="font-semibold tracking-wider">CORE ONLINE</span>
            </>
          ) : (
            <>
              <span className="w-2 h-2 rounded-full bg-matrix-red" />
              <WifiOff className="w-3.5 h-3.5" />
              <span className="font-semibold tracking-wider">OFFLINE</span>
            </>
          )}
        </div>

        {/* Database & Latency */}
        <div className="hidden md:flex items-center gap-2 text-xs font-mono text-slate-400 bg-slate-900/60 px-3 py-1.5 rounded-md border border-slate-800">
          <Clock className="w-3.5 h-3.5 text-matrix-cyan" />
          <span>DB: {health?.database?.connected ? `${dbLatency}ms` : 'Err'}</span>
        </div>

        {/* Active AI Model Badge */}
        <div className="hidden lg:flex items-center gap-2 text-xs font-mono bg-matrix-cyan/10 border border-matrix-cyan/30 text-matrix-cyan px-3 py-1.5 rounded-md">
          <Sparkles className="w-3.5 h-3.5" />
          <span>MODEL: {health?.models?.candidate_local ?? 'Qwen2.5 1.5B Q4'}</span>
          <span className="text-[10px] uppercase px-1.5 py-0.2 rounded bg-matrix-cyan/20 border border-matrix-cyan/30">
            LOCAL-FIRST
          </span>
        </div>
      </div>

      {/* Right: Live Telemetry Gauges & Controls */}
      <div className="flex items-center gap-4">
        {/* CPU Utilization Gauge */}
        <div className="flex items-center gap-2 bg-slate-900/70 border border-slate-800 px-3 py-1 rounded-md text-xs font-mono">
          <Cpu className="w-3.5 h-3.5 text-matrix-cyan" />
          <span className="text-slate-400">CPU</span>
          <span className={`font-semibold ${cpuPercent > 80 ? 'text-matrix-red' : 'text-slate-200'}`}>
            {cpuPercent}%
          </span>
          <div className="w-12 h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-300 ${
                cpuPercent > 80 ? 'bg-matrix-red' : 'bg-matrix-cyan'
              }`}
              style={{ width: `${Math.min(cpuPercent, 100)}%` }}
            />
          </div>
        </div>

        {/* RAM Utilization Gauge */}
        <div className="flex items-center gap-2 bg-slate-900/70 border border-slate-800 px-3 py-1 rounded-md text-xs font-mono">
          <Layers className="w-3.5 h-3.5 text-matrix-blue" />
          <span className="text-slate-400">RAM</span>
          <span className={`font-semibold ${ramPercent > 85 ? 'text-matrix-red' : 'text-slate-200'}`}>
            {ramPercent.toFixed(0)}%
          </span>
          <div className="w-12 h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-300 ${
                ramPercent > 85 ? 'bg-matrix-red' : 'bg-matrix-blue'
              }`}
              style={{ width: `${Math.min(ramPercent, 100)}%` }}
            />
          </div>
        </div>

        {/* Wake Word Microphone Status */}
        <button
          onClick={onToggleVoice}
          className={`p-2 rounded-md border text-xs font-mono flex items-center gap-1.5 transition-all ${
            voiceActive
              ? 'bg-matrix-green/15 border-matrix-green/40 text-matrix-green shadow-[0_0_10px_rgba(0,255,157,0.2)]'
              : 'bg-slate-900/70 border-slate-800 text-slate-400 hover:text-slate-200'
          }`}
          title={voiceActive ? 'Wake Word Active (Hey Matrix)' : 'Voice Inactive'}
        >
          <Radio className={`w-3.5 h-3.5 ${voiceActive ? 'animate-pulse' : ''}`} />
          <span className="hidden sm:inline">{voiceActive ? 'LISTENING' : 'VOICE'}</span>
        </button>

        {/* Audio Output Mute Toggle */}
        <button
          onClick={onToggleMute}
          className={`p-2 rounded-md border text-xs font-mono transition-colors ${
            audioMuted
              ? 'bg-matrix-red/10 border-matrix-red/30 text-matrix-red'
              : 'bg-slate-900/70 border-slate-800 text-slate-400 hover:text-matrix-cyan'
          }`}
          title={audioMuted ? 'Audio Muted' : 'Audio Output Active'}
        >
          {audioMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
        </button>
      </div>
    </header>
  );
};
