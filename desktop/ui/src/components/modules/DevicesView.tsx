import React, { useState, useEffect } from 'react';
import { Smartphone, Wifi, QrCode } from 'lucide-react';

interface DeviceItem {
  id: number;
  device_id: string;
  name: string;
  platform: string;
  is_paired: boolean;
  last_seen_at: string;
  created_at: string;
}

export const DevicesView: React.FC = () => {
  const [devices, setDevices] = useState<DeviceItem[]>([]);
  const [devId, setDevId] = useState('');
  const [devName, setDevName] = useState('');
  const [devPlatform, setDevPlatform] = useState('android');
  const [pairToken, setPairToken] = useState('mtx_pair_manual_test_token');
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const fetchDevices = async () => {
    try {
      const res = await fetch('/api/v1/devices');
      if (res.ok) {
        const data = await res.json();
        setDevices(data);
      }
    } catch {}
  };

  useEffect(() => {
    fetchDevices();
  }, []);

  const handlePair = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!devId.trim() || !devName.trim()) return;
    setLoading(true);
    setStatusMsg(null);
    try {
      const res = await fetch('/api/v1/devices/pair', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: devId,
          name: devName,
          platform: devPlatform,
          pairing_token: pairToken,
        }),
      });
      if (res.ok) {
        setStatusMsg('Device successfully paired and authorized.');
        setDevId('');
        setDevName('');
        fetchDevices();
      } else {
        setStatusMsg('Pairing rejected. Check token format.');
      }
    } catch {
      setStatusMsg('Connection error.');
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async (deviceId: string) => {
    try {
      const res = await fetch(`/api/v1/devices/${deviceId}`, { method: 'DELETE' });
      if (res.ok) {
        fetchDevices();
      }
    } catch {}
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 matrix-grid-bg">
      <div className="flex items-center justify-between border-b border-matrix-border/50 pb-4">
        <div>
          <h1 className="text-sm font-mono uppercase font-bold text-slate-100 flex items-center gap-2">
            <Smartphone className="w-4 h-4 text-matrix-cyan" />
            DEVICE SYNCHRONIZATION & ANDROID BRIDGE
          </h1>
          <p className="text-xs font-mono text-matrix-textMuted mt-0.5">
            Encrypted Device Pairing · Scoped JWT Access Tokens · Bi-directional WebSocket Presence
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Pairing Form */}
        <div className="lg:col-span-5 matrix-glass rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-mono uppercase font-bold text-slate-200 flex items-center gap-2">
              <QrCode className="w-4 h-4 text-matrix-cyan" />
              PAIR NEW DEVICE
            </h2>
          </div>

          <form onSubmit={handlePair} className="space-y-3 font-mono text-xs">
            <div>
              <label className="text-slate-400 block mb-1">Device ID</label>
              <input
                type="text"
                value={devId}
                onChange={(e) => setDevId(e.target.value)}
                placeholder="e.g. pixel_8_pro_ayaan"
                className="w-full h-9 px-3 rounded-lg bg-slate-950 border border-matrix-border text-slate-200 focus:outline-none focus:border-matrix-cyan"
              />
            </div>

            <div>
              <label className="text-slate-400 block mb-1">Friendly Name</label>
              <input
                type="text"
                value={devName}
                onChange={(e) => setDevName(e.target.value)}
                placeholder="e.g. Ayaan's Android Phone"
                className="w-full h-9 px-3 rounded-lg bg-slate-950 border border-matrix-border text-slate-200 focus:outline-none focus:border-matrix-cyan"
              />
            </div>

            <div>
              <label className="text-slate-400 block mb-1">Platform</label>
              <select
                value={devPlatform}
                onChange={(e) => setDevPlatform(e.target.value)}
                className="w-full h-9 px-3 rounded-lg bg-slate-900 border border-slate-700 text-matrix-cyan"
              >
                <option value="android">Android Companion App</option>
                <option value="windows">Windows Secondary PC</option>
                <option value="web">Web Companion Client</option>
              </select>
            </div>

            <div>
              <label className="text-slate-400 block mb-1">Pairing Token</label>
              <input
                type="text"
                value={pairToken}
                onChange={(e) => setPairToken(e.target.value)}
                className="w-full h-9 px-3 rounded-lg bg-slate-950 border border-matrix-border text-slate-400 focus:outline-none"
              />
            </div>

            <button
              type="submit"
              disabled={!devId.trim() || !devName.trim() || loading}
              className="w-full py-2 rounded-lg bg-matrix-cyan text-slate-950 font-bold hover:bg-cyan-300 disabled:opacity-40 transition-colors"
            >
              AUTHORIZE & PAIR DEVICE
            </button>
          </form>

          {statusMsg && (
            <p className="text-xs font-mono text-matrix-cyan mt-1">{statusMsg}</p>
          )}
        </div>

        {/* Registered Devices List */}
        <div className="lg:col-span-7 matrix-glass rounded-xl p-5 space-y-4">
          <h2 className="text-xs font-mono uppercase font-bold text-slate-200">
            REGISTERED DEVICES ({devices.length})
          </h2>

          <div className="space-y-2">
            {devices.map((dev) => (
              <div
                key={dev.device_id}
                className="p-3.5 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between gap-4 font-mono text-xs"
              >
                <div>
                  <div className="font-bold text-slate-200 flex items-center gap-2">
                    <Wifi className="w-3.5 h-3.5 text-matrix-green" />
                    <span>{dev.name}</span>
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-matrix-cyan">
                      {dev.platform.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1">
                    ID: {dev.device_id} · Last Seen: {new Date(dev.last_seen_at).toLocaleTimeString()}
                  </div>
                </div>

                <button
                  onClick={() => handleRevoke(dev.device_id)}
                  className="px-2.5 py-1 rounded bg-matrix-red/15 border border-matrix-red/30 text-matrix-red hover:bg-matrix-red hover:text-white font-bold text-[10px] transition-colors"
                >
                  REVOKE
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
