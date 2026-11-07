import React, { useState, useEffect } from 'react';
import { Brain, Plus, Trash2, ShieldCheck } from 'lucide-react';

interface MemoryItem {
  id: number;
  key: string;
  value: any;
  category: string;
}

export const MemoryView: React.FC = () => {
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [newKey, setNewKey] = useState('');
  const [newVal, setNewVal] = useState('');
  const [newCat, setNewCat] = useState('user_profile');
  const [loading, setLoading] = useState(false);

  const fetchMemories = async () => {
    try {
      const res = await fetch('/api/v1/memory');
      if (res.ok) {
        const data = await res.json();
        setMemories(data);
      }
    } catch {}
  };

  useEffect(() => {
    fetchMemories();
  }, []);

  const handleAddMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKey.trim() || !newVal.trim()) return;
    setLoading(true);
    try {
      let parsedValue: any = newVal;
      try {
        parsedValue = JSON.parse(newVal);
      } catch {
        parsedValue = { note: newVal };
      }

      const res = await fetch('/api/v1/memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: newKey, value: parsedValue, category: newCat }),
      });
      if (res.ok) {
        setNewKey('');
        setNewVal('');
        fetchMemories();
      }
    } catch {}
    finally {
      setLoading(false);
    }
  };

  const handleDelete = async (key: string) => {
    try {
      const res = await fetch(`/api/v1/memory/${key}`, { method: 'DELETE' });
      if (res.ok) {
        fetchMemories();
      }
    } catch {}
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 matrix-grid-bg">
      <div className="flex items-center justify-between border-b border-matrix-border/50 pb-4">
        <div>
          <h1 className="text-sm font-mono uppercase font-bold text-slate-100 flex items-center gap-2">
            <Brain className="w-4 h-4 text-matrix-cyan" />
            LONG-TERM MEMORY & FACTUAL KNOWLEDGE
          </h1>
          <p className="text-xs font-mono text-matrix-textMuted mt-0.5">
            Verified SQLite Entities · Strict User Control · Zero Fabricated Memories
          </p>
        </div>
        <div className="flex items-center gap-1.5 text-xs font-mono px-3 py-1 rounded bg-matrix-green/15 text-matrix-green border border-matrix-green/30">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>HUMAN INSPECTION ENABLED</span>
        </div>
      </div>

      {/* Add Memory Form */}
      <div className="matrix-glass rounded-xl p-5">
        <h2 className="text-xs font-mono uppercase font-bold text-slate-200 mb-3">
          REGISTER USER-APPROVED FACT / PREFERENCE
        </h2>
        <form onSubmit={handleAddMemory} className="grid grid-cols-1 md:grid-cols-12 gap-3">
          <input
            type="text"
            value={newKey}
            onChange={(e) => setNewKey(e.target.value)}
            placeholder="Unique Key (e.g. user_language_pref)"
            className="md:col-span-3 h-10 px-3 rounded-lg bg-slate-950/80 border border-matrix-border text-xs font-mono text-slate-100 focus:outline-none focus:border-matrix-cyan"
          />
          <input
            type="text"
            value={newVal}
            onChange={(e) => setNewVal(e.target.value)}
            placeholder="Value or JSON (e.g. English and Hindi with calm tone)"
            className="md:col-span-5 h-10 px-3 rounded-lg bg-slate-950/80 border border-matrix-border text-xs font-mono text-slate-100 focus:outline-none focus:border-matrix-cyan"
          />
          <select
            value={newCat}
            onChange={(e) => setNewCat(e.target.value)}
            className="md:col-span-2 h-10 px-3 rounded-lg bg-slate-900 border border-slate-700 text-xs font-mono text-matrix-cyan"
          >
            <option value="user_profile">Profile</option>
            <option value="identity">Identity</option>
            <option value="workflow">Workflow</option>
            <option value="hardware">Hardware</option>
          </select>
          <button
            type="submit"
            disabled={!newKey.trim() || !newVal.trim() || loading}
            className="md:col-span-2 h-10 px-4 rounded-lg bg-matrix-cyan text-slate-950 font-mono font-bold text-xs hover:bg-cyan-300 disabled:opacity-40 transition-colors flex items-center justify-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>SAVE</span>
          </button>
        </form>
      </div>

      {/* Memories Table */}
      <div className="matrix-glass rounded-xl p-5 space-y-3">
        <h2 className="text-xs font-mono uppercase font-bold text-slate-200">
          STORED MEMORY ENTITIES ({memories.length})
        </h2>

        <div className="space-y-2">
          {memories.map((mem) => (
            <div
              key={mem.key}
              className="p-3.5 rounded-lg bg-slate-900/60 border border-slate-800 flex items-start justify-between gap-4 font-mono text-xs"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-matrix-cyan">{mem.key}</span>
                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">
                    {mem.category}
                  </span>
                </div>
                <div className="text-slate-300 text-xs mt-1 bg-slate-950/70 p-2 rounded border border-slate-900 overflow-x-auto">
                  {typeof mem.value === 'object' ? JSON.stringify(mem.value, null, 2) : String(mem.value)}
                </div>
              </div>

              <button
                onClick={() => handleDelete(mem.key)}
                className="p-2 rounded hover:bg-matrix-red/20 text-slate-500 hover:text-matrix-red transition-colors flex-shrink-0"
                title="Delete Memory"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
