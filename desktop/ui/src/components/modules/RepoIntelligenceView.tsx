import React, { useState } from 'react';
import {
  GitBranch,
  Star,
  ExternalLink,
  Search,
  Filter,
} from 'lucide-react';
import { STARRED_REPOS, StarredRepo } from '../../data/starredRepos';

export const RepoIntelligenceView: React.FC = () => {
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');

  const categories = [
    'All',
    'Security & MCP',
    'Browser & Web',
    'Voice & Audio',
    'Free LLM Providers',
    'Agent Harnesses',
    'Memory & Context',
    'Creative & Media',
  ];

  const filteredRepos = STARRED_REPOS.filter((repo: StarredRepo) => {
    const matchesCategory =
      selectedCategory === 'All' || repo.category === selectedCategory;
    const matchesSearch =
      repo.full_name.toLowerCase().includes(search.toLowerCase()) ||
      repo.description.toLowerCase().includes(search.toLowerCase()) ||
      repo.language.toLowerCase().includes(search.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 matrix-grid-bg">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-matrix-border/50 pb-4">
        <div>
          <h1 className="text-sm font-mono uppercase font-bold text-slate-100 flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-matrix-cyan" />
            REPOSITORY INTELLIGENCE ENGINE (65 VERIFIED REPOSITORIES)
          </h1>
          <p className="text-xs font-mono text-matrix-textMuted mt-0.5">
            Retrieved via GitHub CLI auth (@ayaanraza2008) · Ready for Phase 10 integration pipeline
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter repositories..."
              className="pl-8 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-matrix-cyan"
            />
          </div>
        </div>
      </div>

      {/* Category Pills */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        <Filter className="w-3.5 h-3.5 text-matrix-cyan flex-shrink-0" />
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`px-3 py-1 rounded-md text-xs font-mono whitespace-nowrap transition-all ${
              selectedCategory === cat
                ? 'bg-matrix-cyan text-slate-950 font-bold shadow-[0_0_8px_#00F0FF]'
                : 'bg-slate-900/80 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Repository Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredRepos.map((repo, idx) => (
          <div
            key={idx}
            className="matrix-glass rounded-xl p-4 flex flex-col justify-between hover:border-matrix-cyan/40 transition-all group relative"
          >
            <div>
              <div className="flex items-start justify-between gap-2">
                <a
                  href={repo.html_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-xs font-bold text-slate-100 group-hover:text-matrix-cyan flex items-center gap-1.5 truncate"
                >
                  <span className="truncate">{repo.full_name}</span>
                  <ExternalLink className="w-3 h-3 flex-shrink-0 opacity-50 group-hover:opacity-100" />
                </a>
                <span className="flex items-center gap-1 text-[11px] font-mono text-matrix-amber flex-shrink-0">
                  <Star className="w-3 h-3 fill-matrix-amber text-matrix-amber" />
                  {repo.stars.toLocaleString()}
                </span>
              </div>

              <p className="text-[11px] font-mono text-slate-400 mt-2 line-clamp-3 leading-relaxed">
                {repo.description}
              </p>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono text-slate-400">
              <div className="flex items-center gap-2">
                <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                  {repo.language}
                </span>
                <span className="truncate max-w-[80px]" title={repo.license}>
                  {repo.license}
                </span>
              </div>

              <span className="px-2 py-0.5 rounded bg-matrix-cyan/10 border border-matrix-cyan/30 text-matrix-cyan truncate max-w-[140px]">
                {repo.integration_method.split(' ')[0]} {repo.integration_method.split(' ')[1]}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
