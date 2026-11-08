import React, { useState, useEffect } from 'react';
import { PhoneCall, Phone, PhoneForwarded, Clock, ShieldCheck, RefreshCw } from 'lucide-react';

interface CallPolicy {
  verified_phone_number: string;
  pstn_calling_enabled: boolean;
  max_calls_per_hour: number;
  quiet_hours_enabled: boolean;
  quiet_hours_start: number;
  quiet_hours_end: number;
  allowed_triggers: string[];
}

interface CallRecord {
  call_id: string;
  direction: string;
  call_type: string;
  from_number: string;
  to_number: string;
  status: string;
  duration_seconds: number;
  trigger_reason: string;
}

export const PhoneCallingView: React.FC = () => {
  const [policy, setPolicy] = useState<CallPolicy | null>(null);
  const [isQuietHours, setIsQuietHours] = useState<boolean>(false);
  const [history, setHistory] = useState<CallRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [delayMinutes, setDelayMinutes] = useState<number>(10);
  const [callStatusMsg, setCallStatusMsg] = useState<string>('');

  const fetchPolicyAndHistory = async () => {
    try {
      const [pRes, hRes] = await Promise.all([
        fetch('/api/v1/telephony/policy'),
        fetch('/api/v1/telephony/history')
      ]);
      if (pRes.ok) {
        const pData = await pRes.json();
        setPolicy(pData.policy);
        setIsQuietHours(pData.is_quiet_hours);
      }
      if (hRes.ok) {
        const hData = await hRes.json();
        setHistory(hData.history || []);
      }
    } catch {}
  };

  useEffect(() => {
    fetchPolicyAndHistory();
  }, []);

  const handleInstantCall = async () => {
    setLoading(true);
    setCallStatusMsg('Initiating call...');
    try {
      const res = await fetch('/api/v1/telephony/call-me', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'Operator initiated in-app voice call from Command Center' })
      });
      const data = await res.json();
      if (res.ok) {
        setCallStatusMsg(`Call connected: ${data.call_id} (${data.provider})`);
        fetchPolicyAndHistory();
      } else {
        setCallStatusMsg(`Call error: ${data.detail || 'Unable to connect'}`);
      }
    } catch (e: any) {
      setCallStatusMsg(`Connection failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleScheduleCall = async () => {
    setLoading(true);
    setCallStatusMsg(`Scheduling call in ${delayMinutes} minutes...`);
    try {
      const res = await fetch('/api/v1/telephony/schedule-call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ delay_minutes: delayMinutes, reason: 'Scheduled callback from operator' })
      });
      const data = await res.json();
      if (res.ok) {
        setCallStatusMsg(data.message || 'Call scheduled successfully');
      } else {
        setCallStatusMsg(`Scheduling error: ${data.detail}`);
      }
    } catch (e: any) {
      setCallStatusMsg(`Scheduling failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 matrix-grid-bg">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-matrix-border/50 pb-4">
        <div>
          <h1 className="text-sm font-mono uppercase font-bold text-slate-100 flex items-center gap-2">
            <PhoneCall className="w-4 h-4 text-matrix-cyan" />
            TWO-WAY TELEPHONY & PHONE CALLING HUB
          </h1>
          <p className="text-xs font-mono text-matrix-textMuted mt-0.5">
            Twilio PSTN Outbound & Inbound · Zero-Cost In-App WebRTC Peer Calling · Strict Safety Policy
          </p>
        </div>
        <button
          onClick={fetchPolicyAndHistory}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-matrix-border bg-matrix-card/60 text-xs font-mono text-slate-300 hover:text-matrix-cyan"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          REFRESH
        </button>
      </div>

      {/* Call Trigger Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Instant Call */}
        <div className="matrix-glass rounded-xl p-5 border border-matrix-cyan/30 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 text-matrix-cyan font-mono text-xs font-bold uppercase tracking-wider mb-2">
              <Phone className="w-4 h-4" />
              Instant In-App / PSTN Call
            </div>
            <p className="text-xs text-slate-300 mb-4 font-mono leading-relaxed">
              Ring your smartphone or current browser session instantly. Converse with MATRIX naturally over full-duplex voice.
            </p>
          </div>
          <div>
            {callStatusMsg && (
              <div className="text-xs font-mono text-matrix-cyan bg-matrix-cyan/10 p-2.5 rounded-lg border border-matrix-cyan/30 mb-3">
                {callStatusMsg}
              </div>
            )}
            <button
              onClick={handleInstantCall}
              disabled={loading}
              className="w-full py-2.5 px-4 rounded-lg bg-matrix-cyan hover:bg-matrix-cyan/80 text-black font-mono font-bold text-xs uppercase flex items-center justify-center gap-2 transition"
            >
              <PhoneCall className="w-4 h-4" />
              {loading ? 'CONNECTING...' : 'CALL MATRIX NOW (ZERO COST)'}
            </button>
          </div>
        </div>

        {/* Scheduled Callback */}
        <div className="matrix-glass rounded-xl p-5 border border-matrix-border flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 text-slate-200 font-mono text-xs font-bold uppercase tracking-wider mb-2">
              <Clock className="w-4 h-4 text-emerald-400" />
              Schedule Matrix Callback
            </div>
            <p className="text-xs text-slate-300 mb-4 font-mono leading-relaxed">
              "Matrix, call me in 10 minutes." Have MATRIX automatically ring you when a milestone completes or on timer.
            </p>
            <div className="flex items-center gap-2 mb-4">
              {[5, 10, 15, 30, 60].map((m) => (
                <button
                  key={m}
                  onClick={() => setDelayMinutes(m)}
                  className={`px-3 py-1.5 rounded-lg font-mono text-xs font-bold border transition ${
                    delayMinutes === m
                      ? 'border-emerald-500 bg-emerald-500/20 text-emerald-300'
                      : 'border-matrix-border bg-matrix-card/40 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {m}m
                </button>
              ))}
            </div>
          </div>
          <button
            onClick={handleScheduleCall}
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-mono font-bold text-xs uppercase flex items-center justify-center gap-2 transition"
          >
            <PhoneForwarded className="w-4 h-4" />
            SCHEDULE CALL IN {delayMinutes} MIN
          </button>
        </div>
      </div>

      {/* Outbound Calling Safety Policy */}
      {policy && (
        <div className="matrix-glass rounded-xl p-5 border border-matrix-border">
          <div className="flex items-center justify-between mb-3 border-b border-matrix-border/40 pb-2">
            <span className="text-xs font-mono font-bold text-slate-200 uppercase flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-matrix-cyan" />
              Outbound Calling Policy & Safety Rules
            </span>
            <span className={`text-xs font-mono px-2 py-0.5 rounded border ${
              isQuietHours
                ? 'border-amber-500/40 bg-amber-500/10 text-amber-400'
                : 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400'
            }`}>
              {isQuietHours ? 'QUIET HOURS ACTIVE' : 'CALLING PERMITTED'}
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono text-xs">
            <div className="p-3 bg-matrix-card/40 rounded-lg border border-matrix-border/50">
              <div className="text-matrix-textMuted text-[10px]">VERIFIED TARGET</div>
              <div className="text-slate-200 font-bold mt-1">{policy.verified_phone_number}</div>
            </div>
            <div className="p-3 bg-matrix-card/40 rounded-lg border border-matrix-border/50">
              <div className="text-matrix-textMuted text-[10px]">PSTN CALLING</div>
              <div className="text-slate-200 font-bold mt-1">{policy.pstn_calling_enabled ? 'ENABLED' : 'IN-APP WEBRTC ONLY'}</div>
            </div>
            <div className="p-3 bg-matrix-card/40 rounded-lg border border-matrix-border/50">
              <div className="text-matrix-textMuted text-[10px]">RATE LIMIT</div>
              <div className="text-slate-200 font-bold mt-1">{policy.max_calls_per_hour} calls / hour</div>
            </div>
            <div className="p-3 bg-matrix-card/40 rounded-lg border border-matrix-border/50">
              <div className="text-matrix-textMuted text-[10px]">QUIET HOURS</div>
              <div className="text-slate-200 font-bold mt-1">{policy.quiet_hours_start}:00 — {policy.quiet_hours_end}:00</div>
            </div>
          </div>
        </div>
      )}

      {/* Call History Table */}
      <div className="matrix-glass rounded-xl p-5 border border-matrix-border">
        <h2 className="text-xs font-mono font-bold text-slate-200 uppercase mb-3">
          Recent Call History & Telemetry
        </h2>
        {history.length === 0 ? (
          <div className="text-xs font-mono text-matrix-textMuted py-6 text-center">
            No call records found. Use the buttons above to initiate or schedule a call.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead>
                <tr className="border-b border-matrix-border/60 text-matrix-textMuted text-[11px]">
                  <th className="pb-2">CALL ID</th>
                  <th className="pb-2">DIRECTION</th>
                  <th className="pb-2">TYPE</th>
                  <th className="pb-2">STATUS</th>
                  <th className="pb-2">DURATION</th>
                  <th className="pb-2">REASON</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-matrix-border/30">
                {history.map((c) => (
                  <tr key={c.call_id} className="hover:bg-matrix-cyan/5 transition">
                    <td className="py-2.5 text-slate-300 font-bold">{c.call_id}</td>
                    <td className="py-2.5 text-slate-400">{c.direction}</td>
                    <td className="py-2.5 text-matrix-cyan">{c.call_type}</td>
                    <td className="py-2.5">
                      <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                        {c.status}
                      </span>
                    </td>
                    <td className="py-2.5 text-slate-400">{c.duration_seconds ? `${c.duration_seconds}s` : '—'}</td>
                    <td className="py-2.5 text-slate-300">{c.trigger_reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
