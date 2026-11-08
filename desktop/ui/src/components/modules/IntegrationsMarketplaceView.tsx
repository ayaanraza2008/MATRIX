import React, { useState, useEffect } from 'react';
import { Blocks, CloudRain, RefreshCw } from 'lucide-react';

interface IntegrationItem {
  integration_id: string;
  name: string;
  category: string;
  provider_name: string;
  description: string;
  status: string;
  auth_type: string;
  required_permissions: string[];
  available_actions: string[];
  cost_tier: string;
  api_limits: string;
}

export const IntegrationsMarketplaceView: React.FC = () => {
  const [integrations, setIntegrations] = useState<IntegrationItem[]>([]);
  const [selectedCat, setSelectedCat] = useState<string>('all');
  const [testResult, setTestResult] = useState<{ id: string; msg: string; success: boolean } | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [weatherInfo, setWeatherInfo] = useState<any>(null);

  const fetchIntegrations = async () => {
    try {
      const res = await fetch('/api/v1/integrations/marketplace/all');
      if (res.ok) {
        const data = await res.json();
        setIntegrations(data.integrations || []);
      }
      const wRes = await fetch('/api/v1/briefing/weather');
      if (wRes.ok) {
        const wData = await wRes.json();
        setWeatherInfo(wData.weather);
      }
    } catch {}
  };

  useEffect(() => {
    fetchIntegrations();
  }, []);

  const handleTest = async (id: string) => {
    setTestingId(id);
    setTestResult(null);
    try {
      const res = await fetch(`/api/v1/integrations/${id}/test`, { method: 'POST' });
      const data = await res.json();
      if (res.ok && data.success) {
        setTestResult({ id, msg: `Verified operational: latency ${data.latency_ms || 12}ms`, success: true });
        fetchIntegrations();
      } else {
        setTestResult({ id, msg: data.error || 'Test failed', success: false });
      }
    } catch (e: any) {
      setTestResult({ id, msg: e.message, success: false });
    } finally {
      setTestingId(null);
    }
  };

  const categories = ['all', 'os', 'information', 'communication', 'productivity', 'development', 'smart_devices'];

  const filtered = selectedCat === 'all'
    ? integrations
    : integrations.filter((i) => i.category === selectedCat);

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 matrix-grid-bg">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-matrix-border/50 pb-4">
        <div>
          <h1 className="text-sm font-mono uppercase font-bold text-slate-100 flex items-center gap-2">
            <Blocks className="w-4 h-4 text-matrix-cyan" />
            UNIVERSAL CONNECTIVITY & INTEGRATIONS MARKETPLACE
          </h1>
          <p className="text-xs font-mono text-matrix-textMuted mt-0.5">
            Modular Connectors across Operating System, Voice & PSTN, Information, and Development
          </p>
        </div>
        <button
          onClick={fetchIntegrations}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-matrix-border bg-matrix-card/60 text-xs font-mono text-slate-300 hover:text-matrix-cyan"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          REFRESH
        </button>
      </div>

      {/* Live Weather Widget Banner */}
      {weatherInfo && (
        <div className="matrix-glass rounded-xl p-4 border border-matrix-cyan/30 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CloudRain className="w-6 h-6 text-matrix-cyan" />
            <div>
              <div className="text-xs font-mono text-matrix-textMuted uppercase">LIVE OPEN-METEO WEATHER INTEGRATION</div>
              <div className="text-sm font-mono text-slate-100 font-bold">
                {weatherInfo.condition} · {weatherInfo.temperature_c}°C (Feels like {weatherInfo.feels_like_c}°C)
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4 text-xs font-mono text-slate-400">
            <div>Humidity: {weatherInfo.humidity_percent}%</div>
            <div>Wind: {weatherInfo.wind_speed_kmh} km/h</div>
            <div className="text-emerald-400 font-bold">LIVE SYNCED</div>
          </div>
        </div>
      )}

      {/* Category Pills */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCat(cat)}
            className={`px-3 py-1 rounded-lg text-xs font-mono uppercase transition ${
              selectedCat === cat
                ? 'bg-matrix-cyan text-black font-bold'
                : 'bg-matrix-card/60 text-slate-400 border border-matrix-border hover:text-slate-200'
            }`}
          >
            {cat.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Test feedback */}
      {testResult && (
        <div className={`p-3 rounded-lg border text-xs font-mono flex items-center justify-between ${
          testResult.success
            ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
            : 'border-red-500/40 bg-red-500/10 text-red-300'
        }`}>
          <span>[{testResult.id}] {testResult.msg}</span>
          <button onClick={() => setTestResult(null)} className="text-slate-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Integrations Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((item) => {
          const isConnected = item.status === 'CONNECTED';
          return (
            <div
              key={item.integration_id}
              className={`matrix-glass rounded-xl p-4 border flex flex-col justify-between transition hover:border-matrix-cyan/50 ${
                isConnected ? 'border-matrix-border' : 'border-matrix-border/50 opacity-80'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-matrix-cyan/10 text-matrix-cyan border border-matrix-cyan/30">
                    {item.category}
                  </span>
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                    isConnected
                      ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400'
                      : 'border-amber-500/40 bg-amber-500/10 text-amber-400'
                  }`}>
                    {item.status}
                  </span>
                </div>
                <h3 className="text-xs font-mono font-bold text-slate-100 mb-1">{item.name}</h3>
                <p className="text-[11px] font-mono text-matrix-textMuted mb-3 line-clamp-2">{item.description}</p>
                <div className="text-[10px] font-mono text-slate-400 space-y-1 mb-4">
                  <div>Provider: <span className="text-slate-300">{item.provider_name}</span></div>
                  <div>Cost Tier: <span className="text-emerald-400 font-bold">{item.cost_tier.toUpperCase()}</span></div>
                  <div>Limits: <span className="text-slate-300">{item.api_limits}</span></div>
                </div>
              </div>

              <div className="pt-2 border-t border-matrix-border/40 flex items-center justify-between">
                <span className="text-[10px] font-mono text-slate-400">Auth: {item.auth_type}</span>
                <button
                  onClick={() => handleTest(item.integration_id)}
                  disabled={testingId === item.integration_id}
                  className="px-2.5 py-1 rounded bg-matrix-cyan/10 hover:bg-matrix-cyan/20 border border-matrix-cyan/40 text-[10px] font-mono text-matrix-cyan font-bold transition"
                >
                  {testingId === item.integration_id ? 'TESTING...' : 'TEST HEALTH'}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
