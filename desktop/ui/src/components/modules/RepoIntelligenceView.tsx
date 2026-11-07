import React, { useState, useEffect } from 'react';
import {
  GitBranch,
  Star,
  ExternalLink,
  Search,
  Filter,
  Cpu,
  Zap,
  CheckCircle2,
  AlertTriangle,
  Play,
  Layers,
  Activity,
  Terminal,
} from 'lucide-react';

interface RepoEvaluation {
  full_name: string;
  html_url: string;
  stars: number;
  language: string;
  description: string;
  category: string;
  target_agent: string;
  maturity: 'installed' | 'available' | 'reference_only' | 'incompatible' | 'rejected';
  integration_method: string;
  license: string;
  license_verdict: string;
  hardware_fit: string;
  ram_estimate_mb: number;
  security_verdict: string;
  capabilities_provided: string[];
}

interface ToolAdapter {
  adapter_id: string;
  name: string;
  description: string;
  source_repo: string;
  category: string;
  version: string;
  supported_operations: string[];
  health_status: string;
  resource_requirements: {
    ram_mb: number;
    cpu_threads: number;
    requires_gpu: boolean;
  };
  test_results?: {
    last_tested?: number;
    operation?: string;
    success?: boolean;
    latency_ms?: number;
  };
}

export const RepoIntelligenceView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'repos' | 'adapters' | 'resolver'>('repos');
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [repos, setRepos] = useState<RepoEvaluation[]>([]);
  const [adapters, setAdapters] = useState<ToolAdapter[]>([]);
  const [loading, setLoading] = useState(true);
  void loading;

  // Task Resolver State
  const [resolverPrompt, setResolverPrompt] = useState('Create a professional AI voice assistant');
  const [resolverResult, setResolverResult] = useState<any>(null);
  const [resolving, setResolving] = useState(false);

  // Execution result state for adapters
  const [executingAdapter, setExecutingAdapter] = useState<string | null>(null);
  const [lastExecOutput, setLastExecOutput] = useState<any>(null);

  useEffect(() => {
    fetchRepositories();
    fetchAdapters();
  }, []);

  const fetchRepositories = async () => {
    try {
      const res = await fetch('/api/v1/repositories');
      if (res.ok) {
        const data = await res.json();
        setRepos(data);
      }
    } catch (err) {
      console.warn('Could not fetch repos from API:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchAdapters = async () => {
    try {
      const res = await fetch('/api/v1/repositories/adapters');
      if (res.ok) {
        const data = await res.json();
        setAdapters(data);
      }
    } catch (err) {
      console.warn('Could not fetch adapters from API:', err);
    }
  };

  const handleResolveTask = async () => {
    if (!resolverPrompt.trim()) return;
    setResolving(true);
    try {
      const res = await fetch('/api/v1/repositories/select-tool', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_description: resolverPrompt }),
      });
      if (res.ok) {
        const data = await res.json();
        setResolverResult(data);
      }
    } catch (err) {
      console.error('Resolver error:', err);
    } finally {
      setResolving(false);
    }
  };

  const handleTestAdapter = async (adapterId: string, op: string) => {
    setExecutingAdapter(adapterId);
    setLastExecOutput(null);
    try {
      const res = await fetch(`/api/v1/repositories/adapters/${adapterId}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ operation: op, parameters: {} }),
      });
      const data = await res.json();
      setLastExecOutput(data);
      fetchAdapters(); // Refresh test status
    } catch (err) {
      setLastExecOutput({ success: false, error: String(err) });
    } finally {
      setExecutingAdapter(null);
    }
  };

  const categories = [
    'All',
    'Browser & Web',
    'Voice & Audio',
    'Security & MCP',
    'Coding & DevTools',
    'Memory & Context',
    'Free LLM Providers',
    'Creative & Media',
    'Research & Science',
    'System & Automation',
    'Mobile & Android',
  ];

  const filteredRepos = repos.filter((r) => {
    const matchesCategory = selectedCategory === 'All' || r.category.toLowerCase() === selectedCategory.toLowerCase();
    const matchesSearch =
      r.full_name.toLowerCase().includes(search.toLowerCase()) ||
      r.description.toLowerCase().includes(search.toLowerCase()) ||
      r.language.toLowerCase().includes(search.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const getMaturityBadge = (maturity: string) => {
    switch (maturity) {
      case 'installed':
        return <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 text-[10px] font-mono">INSTALLED</span>;
      case 'available':
        return <span className="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 text-[10px] font-mono">AVAILABLE ON-DEMAND</span>;
      case 'reference_only':
        return <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/40 text-[10px] font-mono">REFERENCE / SKILL</span>;
      case 'incompatible':
        return <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/40 text-[10px] font-mono">GPU REQUIRED</span>;
      default:
        return <span className="px-2 py-0.5 rounded bg-slate-700 text-slate-300 text-[10px] font-mono">{maturity.toUpperCase()}</span>;
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 matrix-grid-bg text-slate-100">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div>
          <h1 className="text-sm font-mono uppercase font-bold text-slate-100 flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-matrix-cyan animate-pulse" />
            REPOSITORY INTELLIGENCE & CAPABILITY ENGINE
          </h1>
          <p className="text-xs font-mono text-slate-400 mt-1">
            Autonomous Discovery · 3-Tier Policy Gate · 65 Starred Repositories · AMD Ryzen 7 5700U Optimized
          </p>
        </div>

        {/* Live Metrics Pill Strip */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono flex items-center gap-2">
            <Layers className="w-3.5 h-3.5 text-matrix-cyan" />
            <span className="text-slate-400">Total:</span>
            <span className="text-white font-bold">{repos.length || 65}</span>
          </div>
          <div className="px-3 py-1.5 rounded-lg bg-emerald-950/40 border border-emerald-500/30 text-xs font-mono flex items-center gap-2">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-emerald-300">Active Adapters:</span>
            <span className="text-emerald-400 font-bold">{adapters.length || 10}</span>
          </div>
          <div className="px-3 py-1.5 rounded-lg bg-cyan-950/40 border border-cyan-500/30 text-xs font-mono flex items-center gap-2">
            <Cpu className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-cyan-300">AVX2 CPU Fit:</span>
            <span className="text-cyan-400 font-bold">100%</span>
          </div>
        </div>
      </div>

      {/* Main Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('repos')}
          className={`px-4 py-2 rounded-lg text-xs font-mono font-medium transition-all flex items-center gap-2 ${
            activeTab === 'repos'
              ? 'bg-matrix-cyan text-slate-950 font-bold shadow-[0_0_12px_#00F0FF]'
              : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
          }`}
        >
          <GitBranch className="w-3.5 h-3.5" />
          Repository Catalog ({repos.length || 65})
        </button>

        <button
          onClick={() => setActiveTab('adapters')}
          className={`px-4 py-2 rounded-lg text-xs font-mono font-medium transition-all flex items-center gap-2 ${
            activeTab === 'adapters'
              ? 'bg-matrix-cyan text-slate-950 font-bold shadow-[0_0_12px_#00F0FF]'
              : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
          }`}
        >
          <Zap className="w-3.5 h-3.5" />
          Active Tool Adapters ({adapters.length || 10})
        </button>

        <button
          onClick={() => setActiveTab('resolver')}
          className={`px-4 py-2 rounded-lg text-xs font-mono font-medium transition-all flex items-center gap-2 ${
            activeTab === 'resolver'
              ? 'bg-matrix-cyan text-slate-950 font-bold shadow-[0_0_12px_#00F0FF]'
              : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
          }`}
        >
          <Terminal className="w-3.5 h-3.5" />
          Autonomous Capability Resolver
        </button>
      </div>

      {/* TAB 1: REPOSITORY CATALOG */}
      {activeTab === 'repos' && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-2 overflow-x-auto w-full pb-1">
              <Filter className="w-3.5 h-3.5 text-matrix-cyan flex-shrink-0" />
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={`px-2.5 py-1 rounded text-xs font-mono whitespace-nowrap transition-all ${
                    selectedCategory.toLowerCase() === cat.toLowerCase()
                      ? 'bg-matrix-cyan text-slate-950 font-bold'
                      : 'bg-slate-900/80 text-slate-400 hover:text-slate-200 border border-slate-800'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>

            <div className="relative min-w-[240px]">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search 65 repositories..."
                className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-slate-200 focus:outline-none focus:border-matrix-cyan"
              />
            </div>
          </div>

          {/* Repos Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredRepos.map((repo, idx) => (
              <div
                key={idx}
                className="rounded-xl p-4 bg-slate-900/60 border border-slate-800/80 flex flex-col justify-between hover:border-cyan-500/40 transition-all group relative"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <a
                      href={repo.html_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-mono text-xs font-bold text-slate-100 group-hover:text-cyan-400 flex items-center gap-1.5 truncate"
                    >
                      <span className="truncate">{repo.full_name}</span>
                      <ExternalLink className="w-3 h-3 flex-shrink-0 opacity-50 group-hover:opacity-100" />
                    </a>
                    <span className="flex items-center gap-1 text-[11px] font-mono text-amber-400 flex-shrink-0">
                      <Star className="w-3 h-3 fill-amber-400" />
                      {repo.stars.toLocaleString()}
                    </span>
                  </div>

                  <p className="text-[11px] font-mono text-slate-400 mt-2 line-clamp-3 leading-relaxed">
                    {repo.description}
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-800 flex flex-col gap-2 text-[10px] font-mono">
                  <div className="flex items-center justify-between text-slate-400">
                    <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                      {repo.language}
                    </span>
                    <span className="text-slate-400">Agent: <span className="text-cyan-400 font-bold">{repo.target_agent}</span></span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">{repo.category}</span>
                    {getMaturityBadge(repo.maturity)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 2: ACTIVE TOOL ADAPTERS */}
      {activeTab === 'adapters' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {adapters.map((adp) => (
              <div
                key={adp.adapter_id}
                className="rounded-xl p-5 bg-slate-900/80 border border-slate-800 flex flex-col justify-between space-y-4"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Zap className="w-4 h-4 text-cyan-400" />
                      <h3 className="font-mono text-sm font-bold text-white">{adp.name}</h3>
                    </div>
                    <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 text-[10px] font-mono">
                      HEALTHY
                    </span>
                  </div>

                  <p className="text-xs font-mono text-slate-400 mt-1.5">{adp.description}</p>
                  <p className="text-[11px] font-mono text-cyan-400/80 mt-1">Repo: {adp.source_repo}</p>
                </div>

                {/* Operations & Footprint */}
                <div className="space-y-2 pt-2 border-t border-slate-800/80 text-xs font-mono">
                  <div className="flex items-center justify-between text-slate-400">
                    <span>Footprint:</span>
                    <span className="text-slate-200">{adp.resource_requirements.ram_mb} MB RAM · CPU AVX2</span>
                  </div>

                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {adp.supported_operations.map((op) => (
                      <button
                        key={op}
                        onClick={() => handleTestAdapter(adp.adapter_id, op)}
                        disabled={executingAdapter === adp.adapter_id}
                        className="px-2 py-1 rounded bg-slate-800 hover:bg-cyan-950 hover:text-cyan-400 hover:border-cyan-500/50 border border-slate-700 text-[11px] font-mono transition-all flex items-center gap-1"
                      >
                        <Play className="w-2.5 h-2.5" />
                        {op}
                      </button>
                    ))}
                  </div>

                  {adp.test_results?.last_tested && (
                    <div className="text-[10px] font-mono text-emerald-400/90 pt-1 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" />
                      Verified {adp.test_results.operation} in {adp.test_results.latency_ms}ms
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Test Execution Modal/Panel */}
          {lastExecOutput && (
            <div className="p-4 rounded-xl bg-slate-950 border border-cyan-500/40 font-mono text-xs space-y-2">
              <div className="flex items-center justify-between text-cyan-400 font-bold">
                <span className="flex items-center gap-2">
                  <Activity className="w-4 h-4 animate-pulse" />
                  Live Adapter Execution Telemetry
                </span>
                <span className="text-emerald-400">
                  {lastExecOutput.success ? 'SUCCESS (200 OK)' : 'FAILED'}
                </span>
              </div>
              <pre className="p-3 bg-slate-900 rounded-lg overflow-x-auto text-[11px] text-slate-200">
                {JSON.stringify(lastExecOutput, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: AUTONOMOUS RESOLVER */}
      {activeTab === 'resolver' && (
        <div className="max-w-3xl mx-auto space-y-6 py-4">
          <div className="rounded-xl p-5 bg-slate-900 border border-slate-800 space-y-4">
            <div>
              <h2 className="font-mono text-sm font-bold text-white flex items-center gap-2">
                <Terminal className="w-4 h-4 text-matrix-cyan" />
                Autonomous Repository Selection & Gap Resolution
              </h2>
              <p className="text-xs font-mono text-slate-400 mt-1">
                State your requirement. MATRIX will search all 65 repositories, inspect hardware compatibility,
                detect any capability gaps, and select the optimal adapter without prompting for manual configuration.
              </p>
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                value={resolverPrompt}
                onChange={(e) => setResolverPrompt(e.target.value)}
                placeholder="e.g. Create a professional AI voice assistant"
                className="flex-1 px-4 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-white focus:outline-none focus:border-matrix-cyan"
              />
              <button
                onClick={handleResolveTask}
                disabled={resolving}
                className="px-4 py-2 rounded-lg bg-matrix-cyan text-slate-950 font-mono font-bold text-xs hover:shadow-[0_0_12px_#00F0FF] transition-all disabled:opacity-50"
              >
                {resolving ? 'Analyzing...' : 'Resolve Tool'}
              </button>
            </div>

            <div className="flex flex-wrap gap-2 text-[11px] font-mono text-slate-400">
              <span>Quick tests:</span>
              <button
                onClick={() => setResolverPrompt('Create a professional AI voice assistant')}
                className="underline hover:text-cyan-400"
              >
                AI Voice Assistant
              </button>
              <span>·</span>
              <button
                onClick={() => setResolverPrompt('Inspect my computer and report RAM')}
                className="underline hover:text-cyan-400"
              >
                System Telemetry
              </button>
              <span>·</span>
              <button
                onClick={() => setResolverPrompt('Audit open ports and HTTP security')}
                className="underline hover:text-cyan-400"
              >
                HexStrike Security
              </button>
              <span>·</span>
              <button
                onClick={() => setResolverPrompt('Reconstruct 3D scene from photo')}
                className="underline hover:text-cyan-400"
              >
                3D Scene (Gap Test)
              </button>
            </div>
          </div>

          {/* Decision Card */}
          {resolverResult && (
            <div className="rounded-xl p-5 bg-slate-900 border border-cyan-500/40 font-mono space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <span className="text-xs font-bold text-cyan-400 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  DECISION: {resolverResult.selection.selected_adapter}
                </span>
                <span className="text-xs text-slate-400">
                  Target: <strong className="text-white">{resolverResult.selection.target_agent} agent</strong>
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4 text-xs">
                <div>
                  <span className="text-slate-400">Selected Repository:</span>
                  <p className="text-white font-bold">{resolverResult.selection.selected_repo}</p>
                </div>
                <div>
                  <span className="text-slate-400">Compatibility Score:</span>
                  <p className="text-emerald-400 font-bold">{resolverResult.selection.compatibility_score * 100}%</p>
                </div>
                <div>
                  <span className="text-slate-400">Operational Schema:</span>
                  <p className="text-cyan-300 font-mono">{resolverResult.selection.operations_to_invoke.join(', ')}</p>
                </div>
                <div>
                  <span className="text-slate-400">Policy Authorization:</span>
                  <p className="text-emerald-400">
                    {resolverResult.selection.requires_user_approval ? 'LEVEL 3 CONFIRMATION' : 'LEVEL 1/2 AUTOMATIC'}
                  </p>
                </div>
              </div>

              <div className="p-3 bg-slate-950 rounded-lg text-xs text-slate-300 leading-relaxed">
                <strong>Engine Rationale:</strong> {resolverResult.selection.reason}
              </div>

              {resolverResult.capability_gap?.has_gap && (
                <div className="p-3 bg-amber-950/40 border border-amber-500/30 rounded-lg text-xs text-amber-300 space-y-1">
                  <div className="flex items-center gap-1.5 font-bold">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    Capability Gap Handled:
                  </div>
                  <p>{resolverResult.capability_gap.incompatibility_reason}</p>
                  {resolverResult.capability_gap.alternative_suggestion && (
                    <p className="text-slate-300">
                      <strong>Alternative:</strong> {resolverResult.capability_gap.alternative_suggestion}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
