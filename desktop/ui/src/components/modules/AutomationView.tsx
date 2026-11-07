import React, { useState, useEffect } from 'react';
import { Zap, Plus } from 'lucide-react';

interface TaskItem {
  id: number;
  task_id: string;
  title: string;
  autonomy_level: number;
  status: string;
  assigned_agent: string;
  checkpoints?: any;
  created_at: string;
}

export const AutomationView: React.FC = () => {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [newTitle, setNewTitle] = useState('');
  const [newLevel, setNewLevel] = useState(2);
  const [loading, setLoading] = useState(false);

  const fetchTasks = async () => {
    try {
      const res = await fetch('/api/v1/tasks');
      if (res.ok) {
        const data = await res.json();
        setTasks(data);
      }
    } catch {}
  };

  useEffect(() => {
    fetchTasks();
  }, []);

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    setLoading(true);
    try {
      const res = await fetch('/api/v1/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTitle, autonomy_level: newLevel }),
      });
      if (res.ok) {
        setNewTitle('');
        fetchTasks();
      }
    } catch {}
    finally {
      setLoading(false);
    }
  };

  const handleCompleteTask = async (taskId: string) => {
    try {
      const res = await fetch(`/api/v1/tasks/${taskId}/complete`, { method: 'POST' });
      if (res.ok) {
        fetchTasks();
      }
    } catch {}
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 matrix-grid-bg">
      <div className="flex items-center justify-between border-b border-matrix-border/50 pb-4">
        <div>
          <h1 className="text-sm font-mono uppercase font-bold text-slate-100 flex items-center gap-2">
            <Zap className="w-4 h-4 text-matrix-cyan" />
            AUTONOMOUS WORKFLOWS & CHECKPOINT PERSISTENCE
          </h1>
          <p className="text-xs font-mono text-matrix-textMuted mt-0.5">
            Observe → Understand → Plan → Authorize → Execute → Verify → Recover · Persistent SQLite State
          </p>
        </div>
      </div>

      {/* Task Creation Form */}
      <div className="matrix-glass rounded-xl p-5">
        <form onSubmit={handleCreateTask} className="flex flex-col sm:flex-row items-center gap-3">
          <input
            type="text"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Queue a new multi-step automation task (e.g. Daily Document Archival & Checkpoint)..."
            className="flex-1 h-10 px-3 rounded-lg bg-slate-950/80 border border-matrix-border text-xs font-mono text-slate-100 focus:outline-none focus:border-matrix-cyan"
          />
          <select
            value={newLevel}
            onChange={(e) => setNewLevel(Number(e.target.value))}
            className="h-10 px-3 rounded-lg bg-slate-900 border border-slate-700 text-xs font-mono text-matrix-cyan"
          >
            <option value={1}>Autonomy Lvl 1 (Assist)</option>
            <option value={2}>Autonomy Lvl 2 (Plan & Confirm)</option>
            <option value={3}>Autonomy Lvl 3 (Authorized Autonomy)</option>
          </select>
          <button
            type="submit"
            disabled={!newTitle.trim() || loading}
            className="h-10 px-4 rounded-lg bg-matrix-cyan text-slate-950 font-mono font-bold text-xs hover:bg-cyan-300 disabled:opacity-40 transition-colors flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>QUEUE TASK</span>
          </button>
        </form>
      </div>

      {/* Tasks Table */}
      <div className="matrix-glass rounded-xl p-5 space-y-4">
        <h2 className="text-xs font-mono uppercase font-bold text-slate-200">
          PERSISTENT TASK QUEUE & CHECKPOINTS ({tasks.length})
        </h2>

        {tasks.length === 0 ? (
          <p className="text-xs font-mono text-slate-500 py-4 text-center">
            No active automation tasks in SQLite queue. Create one above to test.
          </p>
        ) : (
          <div className="space-y-2">
            {tasks.map((task) => (
              <div
                key={task.task_id}
                className="p-3.5 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between gap-4 font-mono text-xs"
              >
                <div>
                  <div className="font-bold text-slate-200 flex items-center gap-2">
                    <span>{task.title}</span>
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-matrix-cyan">
                      {task.task_id}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-3">
                    <span>Agent: {task.assigned_agent}</span>
                    <span>Autonomy: Level {task.autonomy_level}</span>
                    <span>Created: {new Date(task.created_at).toLocaleTimeString()}</span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                      task.status === 'COMPLETED'
                        ? 'bg-matrix-green/15 text-matrix-green border border-matrix-green/30'
                        : 'bg-matrix-amber/15 text-matrix-amber border border-matrix-amber/30 animate-pulse'
                    }`}
                  >
                    {task.status}
                  </span>

                  {task.status !== 'COMPLETED' && (
                    <button
                      onClick={() => handleCompleteTask(task.task_id)}
                      className="px-2.5 py-1 rounded bg-matrix-cyan/20 border border-matrix-cyan/40 text-matrix-cyan hover:bg-matrix-cyan hover:text-black font-bold text-[10px] transition-colors"
                    >
                      VERIFY & FINISH
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
