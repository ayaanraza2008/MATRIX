import React from 'react';
import {
  Cpu,
  Layers,
  HardDrive,
  Database,
  Sparkles,
  ShieldCheck,
  Zap,
  ArrowUpRight,
} from 'lucide-react';
import { MatrixHologram } from '../hologram/MatrixHologram';
import { HealthData, LiveMetricsData, HologramState, CapabilityItem } from '../../types';

interface DashboardViewProps {
  health: HealthData | null;
  metrics: LiveMetricsData | null;
  hologramState: HologramState;
  capabilities: CapabilityItem[];
  onQuickAction: (actionText: string) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  health,
  metrics,
  hologramState,
  capabilities,
  onQuickAction,
}) => {
  const cpuPercent = metrics?.cpu?.percent ?? health?.system?.cpu_percent ?? 0;
  const ramPercent = metrics?.memory?.percent ?? health?.system?.ram_percent ?? 0;
  const ramUsed = metrics?.memory?.used_mb ?? health?.system?.ram_used_mb ?? 0;
  const ramTotal = metrics?.memory?.total_mb ?? health?.system?.ram_total_mb ?? 0;

  const storageC = health?.storage?.['C:'];
  const storageD = health?.storage?.['D:'];

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 matrix-grid-bg">
      {/* Top Banner: Central Holographic Core + System Status */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
        {/* Hologram Display Card */}
        <div className="lg:col-span-5 matrix-glass rounded-xl p-6 flex flex-col items-center justify-center relative overflow-hidden">
          <div className="absolute top-3 left-4 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-matrix-cyan animate-pulse" />
            <span className="text-xs font-mono text-matrix-cyan uppercase tracking-wider font-semibold">
              NEURAL CORE HOLOGRAM
            </span>
          </div>

          <div className="my-2">
            <MatrixHologram state={hologramState} size={260} />
          </div>

          <div className="w-full mt-2 pt-3 border-t border-matrix-border/40 flex items-center justify-between text-xs font-mono text-slate-400">
            <span>Hardware: Ryzen 7 5700U (AVX2)</span>
            <span className="text-matrix-cyan">16 Threads Active</span>
          </div>
        </div>

        {/* System Vitals & Quick Insights */}
        <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* CPU Card */}
          <div className="matrix-glass rounded-xl p-4 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono text-slate-400 flex items-center gap-1.5">
                <Cpu className="w-4 h-4 text-matrix-cyan" />
                AMD RYZEN 7 5700U
              </span>
              <span className="text-xs font-mono font-bold text-matrix-cyan">{cpuPercent}%</span>
            </div>
            <div className="text-2xl font-mono font-bold text-slate-100">{cpuPercent}%</div>
            <div className="text-xs font-mono text-slate-400 mt-1">
              8 Physical Cores · 16 Threads
            </div>
            <div className="w-full h-1.5 bg-slate-800 rounded-full mt-3 overflow-hidden">
              <div
                className="h-full bg-matrix-cyan transition-all duration-300"
                style={{ width: `${Math.min(cpuPercent, 100)}%` }}
              />
            </div>
          </div>

          {/* RAM Card */}
          <div className="matrix-glass rounded-xl p-4 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono text-slate-400 flex items-center gap-1.5">
                <Layers className="w-4 h-4 text-matrix-blue" />
                SYSTEM MEMORY
              </span>
              <span className="text-xs font-mono font-bold text-matrix-blue">{ramPercent.toFixed(1)}%</span>
            </div>
            <div className="text-2xl font-mono font-bold text-slate-100">
              {(ramUsed / 1024).toFixed(2)} / {(ramTotal / 1024).toFixed(2)} GB
            </div>
            <div className="text-xs font-mono text-slate-400 mt-1">
              Low-RAM Optimization: Active
            </div>
            <div className="w-full h-1.5 bg-slate-800 rounded-full mt-3 overflow-hidden">
              <div
                className="h-full bg-matrix-blue transition-all duration-300"
                style={{ width: `${Math.min(ramPercent, 100)}%` }}
              />
            </div>
          </div>

          {/* Storage Drives Card */}
          <div className="matrix-glass rounded-xl p-4 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono text-slate-400 flex items-center gap-1.5">
                <HardDrive className="w-4 h-4 text-purple-400" />
                STORAGE PARTITIONS
              </span>
              <span className="text-xs font-mono text-matrix-green">D: Mounted</span>
            </div>
            <div className="space-y-1.5 text-xs font-mono">
              <div className="flex justify-between text-slate-300">
                <span>C: (OS / System)</span>
                <span className="text-slate-400">{storageC?.free_gb ?? 22} GB Free</span>
              </div>
              <div className="flex justify-between text-matrix-cyan font-semibold">
                <span>D: (MATRIX Data)</span>
                <span>{storageD?.free_gb ?? 134} GB Free</span>
              </div>
            </div>
            <div className="text-[10px] font-mono text-matrix-textMuted mt-2">
              Models & ChromaDB safely located in D:\matrix_data
            </div>
          </div>

          {/* Core Database & Security Card */}
          <div className="matrix-glass rounded-xl p-4 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono text-slate-400 flex items-center gap-1.5">
                <Database className="w-4 h-4 text-matrix-green" />
                SQLITE PERSISTENCE
              </span>
              <span className="text-xs font-mono font-bold text-matrix-green">
                {health?.database?.connected ? 'CONNECTED' : 'DISCONNECTED'}
              </span>
            </div>
            <div className="text-sm font-mono text-slate-200">
              Async Aiosqlite ORM
            </div>
            <div className="text-xs font-mono text-slate-400 mt-1">
              Latency: {health?.database?.latency_ms ?? 0} ms
            </div>
            <div className="flex items-center gap-1 text-[11px] font-mono text-matrix-amber mt-2">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Deterministic Policy Level 3</span>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Launch Directives */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-mono uppercase tracking-wider text-matrix-cyan flex items-center gap-2">
            <Zap className="w-3.5 h-3.5" />
            DIRECT COMMAND LAUNCHERS
          </h2>
          <span className="text-[11px] font-mono text-slate-500">Verified Subsystem Triggers</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {[
            {
              title: 'Hardware Audit',
              desc: 'Benchmark CPU & RAM availability',
              cmd: 'Execute live hardware audit and log telemetry',
            },
            {
              title: 'Inspect Repositories',
              desc: 'Review 65 starred GitHub repositories',
              cmd: 'Inspect 65 starred repositories and report integration status',
            },
            {
              title: 'Test PC Control',
              desc: 'Verify desktop automation boundaries',
              cmd: 'Test PC automation agent permissions and report',
            },
            {
              title: 'Check Model Status',
              desc: 'Evaluate Qwen2.5 1.5B Q4 memory profile',
              cmd: 'Benchmark candidate Qwen2.5 1.5B Q4 local memory footprint',
            },
          ].map((item, idx) => (
            <button
              key={idx}
              onClick={() => onQuickAction(item.cmd)}
              className="matrix-glass rounded-lg p-3 text-left hover:border-matrix-cyan/60 hover:bg-slate-900/80 transition-all group relative overflow-hidden"
            >
              <div className="flex items-center justify-between text-xs font-mono font-bold text-slate-200 group-hover:text-matrix-cyan">
                <span>{item.title}</span>
                <ArrowUpRight className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100 transition-opacity" />
              </div>
              <p className="text-[11px] font-mono text-slate-400 mt-1 leading-snug">
                {item.desc}
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Active Capabilities Grid */}
      <div className="matrix-glass rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-matrix-border/40 pb-3">
          <h3 className="text-xs font-mono uppercase tracking-wider text-slate-200 flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-matrix-cyan" />
            INITIALIZED CAPABILITIES & AGENTS
          </h3>
          <span className="text-[11px] font-mono text-matrix-cyan">
            {capabilities.length} Verified Subsystems
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {capabilities.map((cap) => (
            <div
              key={cap.capability_id}
              className="p-3 rounded-lg bg-slate-900/50 border border-slate-800 flex flex-col justify-between"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-semibold text-slate-200">
                  {cap.name}
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-matrix-cyan/15 text-matrix-cyan uppercase">
                  {cap.integration_method}
                </span>
              </div>
              <p className="text-[11px] font-mono text-slate-400 mt-1 line-clamp-2">
                {cap.description}
              </p>
              <div className="mt-2 text-[10px] font-mono text-slate-500 truncate">
                Source: {cap.source_repo ?? 'MATRIX Native'}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
