import React, { useState, useEffect } from 'react';
import {
  Settings as SettingsIcon,
  ShieldAlert,
  Lock,
  RefreshCw,
  Key,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Sliders,
  Sparkles,
  Layers,
  Radio,
  Cpu,
  Globe,
} from 'lucide-react';

interface AuditItem {
  id: number;
  event_type: string;
  risk_level: number;
  actor: string;
  action_summary: string;
  status: string;
  timestamp: string;
}

interface ScopeItem {
  id: string;
  scope_id: string;
  name: string;
  description: string;
  category?: string;
  profile: 'AUTOMATIC' | 'RESTRICTED' | 'CONFIRMATION_REQUIRED';
  granted_at: number;
  verified: boolean;
}

interface AuthOverview {
  first_run_completed: boolean;
  setup_timestamp?: number;
  total_scopes: number;
  profile_counts: {
    AUTOMATIC: number;
    RESTRICTED: number;
    CONFIRMATION_REQUIRED: number;
  };
  categories: Record<string, ScopeItem[]>;
  stored_credentials_count: number;
  credential_catalog: Record<string, string>;
}

export const SettingsView: React.FC = () => {
  const [autonomyLevel, setAutonomyLevel] = useState(3);
  const [requireApproval, setRequireApproval] = useState(true);
  const [auditLogs, setAuditLogs] = useState<AuditItem[]>([]);
  const [authData, setAuthData] = useState<AuthOverview | null>(null);
  const [activeCategory, setActiveCategory] = useState<string>('windows_permissions');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [newKey, setNewKey] = useState<string>('');
  const [newVal, setNewVal] = useState<string>('');
  const [vaultMsg, setVaultMsg] = useState<string>('');

  const fetchAuditLogs = async () => {
    try {
      const res = await fetch('/api/v1/audit');
      if (res.ok) {
        const data = await res.json();
        setAuditLogs(data);
      }
    } catch {}
  };

  const fetchAuthData = async () => {
    try {
      const res = await fetch('/api/v1/security/authorization-center');
      if (res.ok) {
        const data: AuthOverview = await res.json();
        setAuthData(data);
      }
    } catch {}
  };

  useEffect(() => {
    fetchAuditLogs();
    fetchAuthData();
  }, []);

  const handleRunSetupWizard = async (template = 'JARVIS_AUTONOMOUS') => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/v1/security/setup-wizard', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template }),
      });
      if (res.ok) {
        await fetchAuthData();
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateProfile = async (category: string, scopeId: string, profile: string) => {
    try {
      const res = await fetch('/api/v1/security/scopes/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category, scope_id: scopeId, profile }),
      });
      if (res.ok) {
        await fetchAuthData();
      }
    } catch {}
  };

  const handleStoreSecret = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKey || !newVal) return;
    try {
      const res = await fetch('/api/v1/security/vault/secret', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: newKey, value: newVal }),
      });
      if (res.ok) {
        setVaultMsg(`Secret '${newKey.toUpperCase()}' encrypted via Windows DPAPI.`);
        setNewKey('');
        setNewVal('');
        await fetchAuthData();
        setTimeout(() => setVaultMsg(''), 4000);
      }
    } catch {
      setVaultMsg('Failed to store secret.');
    }
  };

  const categoryLabels: Record<string, { label: string; icon: any }> = {
    windows_permissions: { label: 'Windows OS Permissions', icon: Cpu },
    connected_services: { label: 'Connected Services & OAuth', icon: Globe },
    hardware: { label: 'Hardware & Audio/Video', icon: Radio },
    repository_tool_access: { label: 'Repositories & Adapters', icon: Layers },
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 matrix-grid-bg">
      {/* Top Header */}
      <div className="flex items-center justify-between border-b border-matrix-border/50 pb-4">
        <div>
          <h1 className="text-sm font-mono uppercase font-bold text-slate-100 flex items-center gap-2">
            <SettingsIcon className="w-4 h-4 text-matrix-cyan" />
            ONE-TIME AUTHORIZATION CENTER & SYSTEM GOVERNANCE
          </h1>
          <p className="text-xs font-mono text-matrix-textMuted mt-0.5">
            Initial Setup Baseline · Scoped Permission Profiles (Automatic / Restricted / Supervised) · Windows DPAPI Credential Vault
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              fetchAuditLogs();
              fetchAuthData();
            }}
            className="p-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-300 hover:text-matrix-cyan transition-colors"
            title="Refresh state"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ONE-TIME SETUP WIZARD & PROFILE OVERVIEW BANNER */}
      <div className="matrix-glass rounded-xl p-5 border border-cyan-500/30 bg-slate-950/60 shadow-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <h2 className="text-sm font-mono uppercase font-bold text-slate-100">
              ONE-TIME AUTHORIZATION STATUS:{' '}
              {authData?.first_run_completed ? (
                <span className="text-emerald-400">PRE-AUTHORIZED & ACTIVE</span>
              ) : (
                <span className="text-amber-400">INITIAL SETUP REQUIRED</span>
              )}
            </h2>
          </div>
          <p className="text-xs font-mono text-slate-400 mt-1 max-w-2xl">
            JARVIS Autonomy Model: Standard routine operations are executed autonomously once authorized.
            Destructive, irreversible, or unverified actions strictly halt for confirmation under Policy Level 4.
          </p>
          <div className="flex items-center gap-4 mt-3 font-mono text-xs">
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
              <CheckCircle2 className="w-3.5 h-3.5" />
              AUTOMATIC: {authData?.profile_counts.AUTOMATIC ?? 0}
            </span>
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30">
              <Sliders className="w-3.5 h-3.5" />
              RESTRICTED: {authData?.profile_counts.RESTRICTED ?? 0}
            </span>
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-purple-500/15 text-purple-300 border border-purple-500/30">
              <AlertTriangle className="w-3.5 h-3.5" />
              SUPERVISED: {authData?.profile_counts.CONFIRMATION_REQUIRED ?? 0}
            </span>
          </div>
        </div>

        <button
          onClick={() => handleRunSetupWizard('JARVIS_AUTONOMOUS')}
          disabled={isLoading}
          className="px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-mono text-xs font-bold tracking-wider flex items-center gap-2 shadow-lg shadow-cyan-950/40 border border-cyan-400/30 transition-all shrink-0 cursor-pointer"
        >
          <Sparkles className="w-4 h-4 text-cyan-200" />
          {authData?.first_run_completed ? 'RE-RUN ONE-TIME SETUP' : 'RUN JARVIS SETUP WIZARD'}
        </button>
      </div>

      {/* CATEGORY SCOPES MANAGEMENT SECTION */}
      <div className="matrix-glass rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <h2 className="text-xs font-mono uppercase font-bold text-slate-200 flex items-center gap-2">
            <Sliders className="w-4 h-4 text-matrix-cyan" />
            AUTHORIZATION SCOPES BY CATEGORY
          </h2>
          <span className="text-[11px] font-mono text-slate-500">
            Total Scopes Managed: {authData?.total_scopes ?? 0}
          </span>
        </div>

        {/* Category Selector Tabs */}
        <div className="flex flex-wrap gap-2">
          {authData?.categories &&
            Object.keys(authData.categories).map((catKey) => {
              const meta = categoryLabels[catKey] || { label: catKey, icon: Layers };
              const IconComp = meta.icon;
              const isActive = activeCategory === catKey;
              return (
                <button
                  key={catKey}
                  onClick={() => setActiveCategory(catKey)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg font-mono text-xs transition-all cursor-pointer ${
                    isActive
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold'
                      : 'bg-slate-900/60 text-slate-400 border border-slate-800 hover:text-slate-200'
                  }`}
                >
                  <IconComp className="w-3.5 h-3.5" />
                  <span>{meta.label}</span>
                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">
                    {authData.categories[catKey]?.length ?? 0}
                  </span>
                </button>
              );
            })}
        </div>

        {/* Scopes Grid for Active Category */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pt-2">
          {authData?.categories[activeCategory]?.map((scope) => {
            const isAuto = scope.profile === 'AUTOMATIC';
            const isRestricted = scope.profile === 'RESTRICTED';
            return (
              <div
                key={scope.id}
                className="p-3.5 rounded-lg bg-slate-950/80 border border-slate-800/80 flex flex-col justify-between gap-3 font-mono text-xs hover:border-slate-700 transition-all"
              >
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-slate-200 font-bold truncate">{scope.name}</span>
                    <span
                      className={`text-[9px] px-2 py-0.5 rounded font-bold uppercase tracking-wider shrink-0 ${
                        isAuto
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          : isRestricted
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          : 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                      }`}
                    >
                      {scope.profile}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1 leading-relaxed line-clamp-2">
                    {scope.description}
                  </p>
                </div>

                <div className="flex items-center gap-1.5 pt-2 border-t border-slate-900">
                  <button
                    onClick={() => handleUpdateProfile(activeCategory, scope.scope_id, 'AUTOMATIC')}
                    className={`flex-1 py-1 text-[10px] rounded font-bold tracking-wider cursor-pointer ${
                      isAuto ? 'bg-emerald-600 text-white' : 'bg-slate-900 text-slate-400 hover:text-emerald-300'
                    }`}
                  >
                    AUTO
                  </button>
                  <button
                    onClick={() => handleUpdateProfile(activeCategory, scope.scope_id, 'RESTRICTED')}
                    className={`flex-1 py-1 text-[10px] rounded font-bold tracking-wider cursor-pointer ${
                      isRestricted ? 'bg-amber-600 text-white' : 'bg-slate-900 text-slate-400 hover:text-amber-300'
                    }`}
                  >
                    LIMIT
                  </button>
                  <button
                    onClick={() => handleUpdateProfile(activeCategory, scope.scope_id, 'CONFIRMATION_REQUIRED')}
                    className={`flex-1 py-1 text-[10px] rounded font-bold tracking-wider cursor-pointer ${
                      scope.profile === 'CONFIRMATION_REQUIRED'
                        ? 'bg-purple-600 text-white'
                        : 'bg-slate-900 text-slate-400 hover:text-purple-300'
                    }`}
                  >
                    CONFIRM
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* TWO COLUMN GRID: DPAPI CREDENTIAL VAULT & AUTONOMY LEVEL */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Native Windows DPAPI Credential Vault Card */}
        <div className="matrix-glass rounded-xl p-5 space-y-4 font-mono text-xs">
          <div className="flex items-center justify-between">
            <h2 className="text-xs uppercase font-bold text-slate-200 flex items-center gap-2">
              <Key className="w-4 h-4 text-matrix-cyan" />
              WINDOWS DPAPI HARDWARE CREDENTIAL VAULT
            </h2>
            <span className="text-[10px] px-2 py-0.5 rounded bg-matrix-green/15 text-matrix-green font-bold">
              ENCRYPTED ON DISK
            </span>
          </div>

          <p className="text-[11px] text-slate-400 leading-relaxed">
            Secrets are encrypted using Windows CryptProtectData tied to your Windows user account.
            Never stored in Git, logs, or plaintext.
          </p>

          {/* Stored Keys Catalog */}
          <div className="space-y-1.5 max-h-36 overflow-y-auto">
            {authData?.credential_catalog && Object.keys(authData.credential_catalog).length > 0 ? (
              Object.entries(authData.credential_catalog).map(([k, masked]) => (
                <div
                  key={k}
                  className="flex items-center justify-between p-2 rounded bg-slate-950/80 border border-slate-800 text-[11px]"
                >
                  <span className="text-cyan-300 font-bold">{k}</span>
                  <span className="text-slate-500 font-mono">{masked}</span>
                </div>
              ))
            ) : (
              <div className="p-3 text-slate-500 text-center bg-slate-950/40 rounded border border-slate-900">
                No external API keys in vault. Using local-first CPU inference.
              </div>
            )}
          </div>

          {/* Add Secret Form */}
          <form onSubmit={handleStoreSecret} className="space-y-2 pt-2 border-t border-slate-800">
            <div className="grid grid-cols-2 gap-2">
              <input
                type="text"
                placeholder="KEY_NAME (e.g. BLAND_API_KEY)"
                value={newKey}
                onChange={(e) => setNewKey(e.target.value)}
                className="bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 placeholder-slate-500 text-[11px]"
              />
              <input
                type="password"
                placeholder="Secret Value"
                value={newVal}
                onChange={(e) => setNewVal(e.target.value)}
                className="bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 placeholder-slate-500 text-[11px]"
              />
            </div>
            <div className="flex items-center justify-between">
              {vaultMsg && <span className="text-[10px] text-emerald-400">{vaultMsg}</span>}
              <button
                type="submit"
                className="ml-auto px-3 py-1 rounded bg-slate-800 hover:bg-cyan-600 text-slate-200 hover:text-white font-bold text-[11px] transition-colors cursor-pointer"
              >
                Store in DPAPI Vault
              </button>
            </div>
          </form>
        </div>

        {/* System Autonomy Governance Card */}
        <div className="matrix-glass rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-mono uppercase font-bold text-slate-200 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-matrix-amber" />
              CENTRAL AUTONOMY POLICY
            </h2>
            <span className="text-xs font-mono font-bold text-matrix-amber">
              LEVEL {autonomyLevel} ACTIVE
            </span>
          </div>

          <div className="space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between text-slate-300">
              <span>Operational Mode:</span>
              <span className="text-matrix-cyan font-bold">
                {autonomyLevel === 0 && 'Level 0: Informational / Suggestion Only'}
                {autonomyLevel === 1 && 'Level 1: Assist (Read-Only Commands)'}
                {autonomyLevel === 2 && 'Level 2: Plan & Request Confirmation'}
                {autonomyLevel === 3 && 'Level 3: JARVIS Autonomy (Default)'}
                {autonomyLevel === 4 && 'Level 4: Supervised / Monitored'}
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
              <span className="text-slate-300">Strict Confirmation Gate for Irreversible Actions:</span>
              <button
                onClick={() => setRequireApproval(!requireApproval)}
                className={`px-3 py-1 rounded text-xs font-bold cursor-pointer ${
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
      </div>

      {/* Security Audit Trail Table */}
      <div className="matrix-glass rounded-xl p-5 space-y-3">
        <h2 className="text-xs font-mono uppercase font-bold text-slate-200 flex items-center gap-2">
          <Lock className="w-4 h-4 text-matrix-cyan" />
          IMMUTABLE SECURITY AUDIT TRAIL ({auditLogs.length} ENTRIES)
        </h2>

        <div className="space-y-1.5 max-h-60 overflow-y-auto">
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
                      log.status === 'ALLOWED' || log.status === 'APPROVED' || log.status === 'SUCCESS'
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
