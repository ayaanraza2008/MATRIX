import React from 'react';
import {
  Activity,
  Cpu,
  Layers,
  HardDrive,
  Database,
  Terminal,
} from 'lucide-react';
import { HealthData, LiveMetricsData, SystemInfoData } from '../../types';

interface SystemMonitorViewProps {
  health: HealthData | null;
  metrics: LiveMetricsData | null;
  systemInfo: SystemInfoData | null;
}

export const SystemMonitorView: React.FC<SystemMonitorViewProps> = ({
  health,
  metrics,
  systemInfo,
}) => {
  const cpuPercent = metrics?.cpu?.percent ?? health?.system?.cpu_percent ?? 0;
  const ramPercent = metrics?.memory?.percent ?? health?.system?.ram_percent ?? 0;
  const ramUsed = metrics?.memory?.used_mb ?? health?.system?.ram_used_mb ?? 0;
  const ramAvailable = metrics?.memory?.available_mb ?? health?.system?.ram_available_mb ?? 0;
  const ramTotal = metrics?.memory?.total_mb ?? health?.system?.ram_total_mb ?? 0;

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 matrix-grid-bg">
      <div className="flex items-center justify-between border-b border-matrix-border/50 pb-4">
        <div>
          <h1 className="text-sm font-mono uppercase font-bold text-slate-100 flex items-center gap-2">
            <Activity className="w-4 h-4 text-matrix-cyan" />
            SYSTEM HARDWARE & TELEMETRY MONITOR
          </h1>
          <p className="text-xs font-mono text-matrix-textMuted mt-0.5">
            Verified machine telemetry: AMD Ryzen 7 5700U (Zen 2) · Windows 11 x64
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded bg-matrix-cyan/15 text-matrix-cyan border border-matrix-cyan/30">
          <span>AVX2 ACCELERATED</span>
        </div>
      </div>

      {/* Primary Hardware Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* CPU Deep Card */}
        <div className="matrix-glass rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400 flex items-center gap-1.5">
              <Cpu className="w-4 h-4 text-matrix-cyan" />
              PROCESSOR PROFILE
            </span>
            <span className="text-xs font-mono font-bold text-matrix-cyan">{cpuPercent}% LOAD</span>
          </div>

          <div className="text-base font-mono font-bold text-slate-100">
            AMD Ryzen 7 5700U
          </div>
          <div className="space-y-1 text-xs font-mono text-slate-400 border-t border-slate-800 pt-2">
            <div className="flex justify-between">
              <span>Physical Cores:</span>
              <span className="text-slate-200">8 Cores</span>
            </div>
            <div className="flex justify-between">
              <span>Logical Processors:</span>
              <span className="text-slate-200">16 Threads</span>
            </div>
            <div className="flex justify-between">
              <span>SIMD Instruction Set:</span>
              <span className="text-matrix-cyan">AVX2 Supported</span>
            </div>
          </div>
        </div>

        {/* Memory Deep Card */}
        <div className="matrix-glass rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400 flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-matrix-blue" />
              MEMORY TOPOLOGY
            </span>
            <span className="text-xs font-mono font-bold text-matrix-blue">
              {ramPercent.toFixed(1)}% USED
            </span>
          </div>

          <div className="text-base font-mono font-bold text-slate-100">
            {(ramTotal / 1024).toFixed(2)} GB Visible RAM
          </div>
          <div className="space-y-1 text-xs font-mono text-slate-400 border-t border-slate-800 pt-2">
            <div className="flex justify-between">
              <span>Used Memory:</span>
              <span className="text-slate-200">{ramUsed.toFixed(0)} MB</span>
            </div>
            <div className="flex justify-between">
              <span>Available Memory:</span>
              <span className="text-matrix-green">{ramAvailable.toFixed(0)} MB</span>
            </div>
            <div className="flex justify-between">
              <span>Governor Policy:</span>
              <span className="text-matrix-amber">Low-RAM Safe Mode</span>
            </div>
          </div>
        </div>

        {/* Graphics & Acceleration Card */}
        <div className="matrix-glass rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400 flex items-center gap-1.5">
              <Terminal className="w-4 h-4 text-purple-400" />
              GRAPHICS SUBSYSTEM
            </span>
            <span className="text-xs font-mono text-matrix-green">ACTIVE</span>
          </div>

          <div className="text-base font-mono font-bold text-slate-100">
            AMD Radeon(TM) Graphics
          </div>
          <div className="space-y-1 text-xs font-mono text-slate-400 border-t border-slate-800 pt-2">
            <div className="flex justify-between">
              <span>Type:</span>
              <span className="text-slate-200">Integrated APU</span>
            </div>
            <div className="flex justify-between">
              <span>Dedicated VRAM:</span>
              <span className="text-slate-200">512 MB</span>
            </div>
            <div className="flex justify-between">
              <span>Inference Strategy:</span>
              <span className="text-matrix-cyan">AVX2 CPU Kernels</span>
            </div>
          </div>
        </div>
      </div>

      {/* Storage and Database Telemetry */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="matrix-glass rounded-xl p-5 space-y-3">
          <h3 className="text-xs font-mono uppercase text-slate-300 flex items-center gap-2">
            <HardDrive className="w-4 h-4 text-matrix-cyan" />
            STORAGE VOLUMES
          </h3>
          <div className="space-y-3 text-xs font-mono">
            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
              <div className="flex justify-between font-bold text-slate-200">
                <span>C: Primary Volume (Windows 11)</span>
                <span>{health?.storage?.['C:']?.free_gb ?? 22} GB Free</span>
              </div>
              <div className="w-full h-1.5 bg-slate-800 rounded-full mt-2 overflow-hidden">
                <div
                  className="h-full bg-slate-500"
                  style={{ width: `${health?.storage?.['C:']?.used_percent ?? 85}%` }}
                />
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-900/60 border border-matrix-cyan/30">
              <div className="flex justify-between font-bold text-matrix-cyan">
                <span>D: MATRIX Storage Partition</span>
                <span>{health?.storage?.['D:']?.free_gb ?? 134} GB Free</span>
              </div>
              <div className="w-full h-1.5 bg-slate-800 rounded-full mt-2 overflow-hidden">
                <div
                  className="h-full bg-matrix-cyan"
                  style={{ width: `${health?.storage?.['D:']?.used_percent ?? 15}%` }}
                />
              </div>
              <div className="text-[10px] text-slate-400 mt-2">
                Mount: D:\matrix_data (Preserves OS drive headroom)
              </div>
            </div>
          </div>
        </div>

        {/* Database & Runtime Diagnostics */}
        <div className="matrix-glass rounded-xl p-5 space-y-3">
          <h3 className="text-xs font-mono uppercase text-slate-300 flex items-center gap-2">
            <Database className="w-4 h-4 text-matrix-green" />
            RUNTIME PERSISTENCE
          </h3>
          <div className="space-y-2 text-xs font-mono text-slate-300">
            <div className="flex justify-between p-2.5 rounded bg-slate-900/50 border border-slate-800">
              <span>Engine:</span>
              <span className="text-matrix-cyan">{health?.database?.type ?? 'SQLite (Async)'}</span>
            </div>
            <div className="flex justify-between p-2.5 rounded bg-slate-900/50 border border-slate-800">
              <span>Database Path:</span>
              <span className="text-slate-400 truncate max-w-xs">{health?.database?.path ?? 'D:\\matrix_data\\matrix.db'}</span>
            </div>
            <div className="flex justify-between p-2.5 rounded bg-slate-900/50 border border-slate-800">
              <span>Ping Latency:</span>
              <span className="text-matrix-green">{health?.database?.latency_ms ?? 0} ms</span>
            </div>
            <div className="flex justify-between p-2.5 rounded bg-slate-900/50 border border-slate-800">
              <span>Python Version:</span>
              <span className="text-slate-300">{systemInfo?.python?.version ?? '3.12.10'}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
