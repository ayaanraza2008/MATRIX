import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, ShieldAlert, Lock, Database, RefreshCw } from 'lucide-react';

interface AuditItem {
  id: number;
  event_type: string;
  risk_level: number;
  actor: string;
  action_summary: string;
  status: string;
  timestamp: string;
}

export const SettingsView: React.FC = () => {
  const [autonomyLevel, setAutonomyLevel] = useState(3);
  const [requireApproval, setRequireApproval] = useState(true);
  const [auditLogs, setAuditLogs] = useState<AuditItem[]>([]);

  const fetchAuditLogs = async () => {
    try {
      const res = await fetch('/api/v1/audit');
      if (res.ok) {
        const data = await res.json();
        setAuditLogs(data);
      }
    } catch {}
  };

  useEffect(() => {
    fetchAuditLogs();
  }, []);

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 matrix-grid-bg">
      <div className="flex items-center justify-between border-b border-matrix-border/50 pb-4">
        <div>
          <h1 className="text-sm font-mono uppercase font-bold text-slate-100 flex items-center gap-2">
            <SettingsIcon className="w-4 h-4 text-matrix-cyan" />
            SYSTEM GOVERNANCE & SECURITY AUDIT
          </h1>
          <p className="text-xs font-mono text-matrix-textMuted mt-0.5">
            Deterministic Policy Gates (Level 0–4) · Sandboxed Execution · Tamper-evident Audit Trails
          </p>
        </div>
        <button
          onClick={fetchAuditLogs}
          className="p-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-300 hover:text-matrix-cyan transition-colors"
          title="Refresh audit log"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Autonomy Level Control Card */}
        <div className="matrix-glass rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-mono uppercase font-bold text-slate-200 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-matrix-amber" />
              AUTONOMY POLICY LEVEL
            </h2>
            <span className="text-xs font-mono font-bold text-matrix-amber">
              LEVEL {autonomyLevel} ACTIVE
            </span>
          </div>

          <div className="space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between text-slate-300">
              <span>Security Level:</span>
              <span className="text-matrix-cyan font-bold">
                {autonomyLevel === 0 && 'Level 0: Informational Only'}
                {autonomyLevel === 1 && 'Level 1: Assist (Read-Only Commands)'}
                {autonomyLevel === 2 && 'Level 2: Plan & Request Confirmation'}
                {autonomyLevel === 3 && 'Level 3: Authorized Autonomy (Default)'}
                {autonomyLevel === 4 && 'Level 4: Monitored Autonomy'}
              </span>
            </div>

            <input
              type="range"
              min={0}
              max={4}
              value={autonomyLevel}
              onChange={(e) => setAutonomyLevel(Number(e.target.value))}
              className="w-full accent-cyan-400 cursor-pointer"
            />

            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="text-slate-300">Require Human Approval for Level ≥ 3:</span>
              <button
                onClick={() => setRequireApproval(!requireApproval)}
                className={`px-3 py-1 rounded text-xs font-bold ${
                  requireApproval
                    ? 'bg-matrix-green/20 text-matrix-green border border-matrix-green/40'
                    : 'bg-slate-800 text-slate-400'
                }`}
              >
                {requireApproval ? 'ENFORCED' : 'DISABLED'}
              </button>
            </div>
          </div>
        </div>

        {/* Storage Partitions Card */}
        <div className="matrix-glass rounded-xl p-5 space-y-4 font-mono text-xs">
          <h2 className="text-xs uppercase font-bold text-slate-200 flex items-center gap-2">
            <Database className="w-4 h-4 text-matrix-cyan" />
            STORAGE & DIRECTORY GOVERNANCE
          </h2>

          <div className="space-y-2">
            <div className="p-3 rounded-lg bg-slate-950/80 border border-matrix-cyan/30 flex justify-between items-center">
              <div>
                <div className="text-matrix-cyan font-bold">Data & Models Root</div>
                <div className="text-slate-400 text-[11px]">D:\matrix_data\</div>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded bg-matrix-green/15 text-matrix-green">
                PROTECTED
              </span>
            </div>

            <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 flex justify-between items-center">
              <div>
                <div className="text-slate-300 font-bold">SQLite Persistence</div>
                <div className="text-slate-400 text-[11px]">D:\matrix_data\matrix.db</div>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded bg-matrix-cyan/15 text-matrix-cyan">
                ASYNC AIOSQLITE
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Security Audit Trail Table */}
      <div className="matrix-glass rounded-xl p-5 space-y-3">
        <h2 className="text-xs font-mono uppercase font-bold text-slate-200 flex items-center gap-2">
          <Lock className="w-4 h-4 text-matrix-cyan" />
          IMMUTABLE SECURITY AUDIT TRAIL ({auditLogs.length} ENTRIES)
        </h2>

        <div className="space-y-1.5 max-h-72 overflow-y-auto">
          {auditLogs.map((log) => (
            <div
              key={log.id}
              className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between gap-4 font-mono text-xs"
            >
              <div className="flex-1 truncate">
                <div className="flex items-center gap-2">
                  <span className="text-matrix-cyan font-bold">{log.event_type}</span>
                  <span className="text-[10px] text-slate-500">[{log.actor}]</span>
                  <span
                    className={`text-[9px] px-1.5 py-0.2 rounded font-bold ${
                      log.status === 'ALLOWED' || log.status === 'APPROVED'
                        ? 'bg-matrix-green/15 text-matrix-green'
                        : 'bg-matrix-red/15 text-matrix-red'
                    }`}
                  >
                    {log.status}
                  </span>
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5 truncate">{log.action_summary}</div>
              </div>

              <span className="text-[10px] text-slate-500 flex-shrink-0">
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
