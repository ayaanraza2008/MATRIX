import React, { useState } from 'react';
import { Globe, Search, BookOpen, CheckCircle2 } from 'lucide-react';

export const ResearchView: React.FC = () => {
  const [query, setQuery] = useState('autonomous agent architectures 2026');
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<string | null>(null);

  const handleResearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setReport(null);

    try {
      const res = await fetch('/api/v1/sessions/sess_research/interact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          role: 'user',
          content: `Search the web and compile a research report on: ${query}`,
          agent_name: 'research',
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setReport(data.reply);
      }
    } catch {
      setReport('Failed to complete research query.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 matrix-grid-bg">
      <div className="flex items-center justify-between border-b border-matrix-border/50 pb-4">
        <div>
          <h1 className="text-sm font-mono uppercase font-bold text-slate-100 flex items-center gap-2">
            <Globe className="w-4 h-4 text-matrix-cyan" />
            DEEP RESEARCH & FACT VERIFICATION AGENT
          </h1>
          <p className="text-xs font-mono text-matrix-textMuted mt-0.5">
            Multi-source web search · Contradiction checking · Structured citation dossiers
          </p>
        </div>
      </div>

      <div className="matrix-glass rounded-xl p-5">
        <form onSubmit={handleResearch} className="flex gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-matrix-cyan absolute left-3.5 top-3" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter research inquiry (e.g. quantum algorithms, Qwen2.5 quantization benchmarks)..."
              className="w-full h-10 pl-10 pr-3 rounded-lg bg-slate-950/80 border border-matrix-border text-xs font-mono text-slate-100 focus:outline-none focus:border-matrix-cyan"
            />
          </div>
          <button
            type="submit"
            disabled={!query.trim() || loading}
            className="px-5 h-10 rounded-lg bg-matrix-cyan text-slate-950 font-mono font-bold text-xs hover:bg-cyan-300 disabled:opacity-40 transition-colors flex items-center gap-1.5"
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>{loading ? 'RESEARCHING...' : 'DISPATCH AGENT'}</span>
          </button>
        </form>
      </div>

      {report && (
        <div className="matrix-glass rounded-xl p-6 space-y-4 font-mono text-xs text-slate-200">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <span className="font-bold text-matrix-cyan flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-matrix-green" />
              VERIFIED RESEARCH DOSSIER
            </span>
            <span className="text-[10px] text-slate-400">Multi-source Web Extraction</span>
          </div>

          <div className="whitespace-pre-wrap leading-relaxed space-y-2">
            {report}
          </div>
        </div>
      )}
    </div>
  );
};
