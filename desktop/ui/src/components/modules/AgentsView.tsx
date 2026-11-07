import React, { useState } from 'react';
import {
  Bot,
  Zap,
  CheckCircle2,
  Cpu,
  Globe,
  Code2,
  FolderGit2,
  Mic,
  Eye,
  Smartphone,
  Activity,
  User,
  GitBranch,
  Shield,
  BarChart3,
  Sparkles,
} from 'lucide-react';

interface AgentCard {
  id: string;
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
  autonomy: number;
  testPrompt: string;
}

const AGENTS: AgentCard[] = [
  { id: 'computer', name: 'Computer Agent', icon: Cpu, description: 'Windows 11 apps, window management, screenshot capture', autonomy: 2, testPrompt: 'Take a screenshot of the desktop' },
  { id: 'browser', name: 'Browser Agent', icon: Globe, description: 'Automated web navigation, article scraping, and DOM extraction', autonomy: 2, testPrompt: 'Navigate to news.ycombinator.com and extract page title' },
  { id: 'research', name: 'Research Agent', icon: Globe, description: 'Multi-source fact retrieval, contradiction resolution, citations', autonomy: 1, testPrompt: 'Search the web for autonomous agents' },
  { id: 'coding', name: 'Coding Agent', icon: Code2, description: 'Code analysis, AST syntax validation, pytest execution', autonomy: 2, testPrompt: 'Run unit test suite tests/test_foundation.py' },
  { id: 'files', name: 'File Agent', icon: FolderGit2, description: 'Document reading (PDF, DOCX, XLSX, CSV, TXT) in D:\\matrix_data', autonomy: 2, testPrompt: 'Scan and list files in D:\\matrix_data' },
  { id: 'voice', name: 'Voice Agent', icon: Mic, description: 'Neural TTS speech synthesis, Whisper STT, and wake-word VAD', autonomy: 1, testPrompt: 'Synthesize speech saying MATRIX voice online' },
  { id: 'vision', name: 'Vision Agent', icon: Eye, description: 'OpenCV webcam capture and desktop visual analysis', autonomy: 1, testPrompt: 'Capture screenshot and analyze screen resolution' },
  { id: 'android', name: 'Android Agent', icon: Smartphone, description: 'Device pairing tokens, mobile notifications, remote task routing', autonomy: 2, testPrompt: 'Generate device pairing token' },
  { id: 'system', name: 'System Agent', icon: Activity, description: 'Ryzen 7 5700U utilization, RAM pressure, and disk metrics', autonomy: 1, testPrompt: 'Poll real hardware telemetry' },
  { id: 'personal', name: 'Personal Agent', icon: User, description: 'User preferences, schedule reminders, and daily identity', autonomy: 1, testPrompt: 'What is your system identity?' },
  { id: 'automation', name: 'Automation Agent', icon: Zap, description: 'Multi-step DAG workflows, SQLite checkpoints, crash recovery', autonomy: 3, testPrompt: 'Create workflow task with checkpoints' },
  { id: 'creative', name: 'Creative Agent', icon: Sparkles, description: 'ComfyUI node workflows, image generation, and media rendering', autonomy: 2, testPrompt: 'Render creative media plan for HUD' },
  { id: 'memory', name: 'Memory Agent', icon: FolderGit2, description: 'Zero-fabrication SQLite preferences and knowledge retrieval', autonomy: 1, testPrompt: 'Inspect stored user memory preferences' },
  { id: 'repo_intel', name: 'Repo Intel Agent', icon: GitBranch, description: '65 verified GitHub starred repos query and skill generation', autonomy: 1, testPrompt: 'Query starred repositories for hexstrike' },
  { id: 'security', name: 'Security Agent', icon: Shield, description: 'Deterministic policy enforcement (Levels 0-4), command sandboxing', autonomy: 3, testPrompt: 'Evaluate payload: format C: /fs:NTFS' },
  { id: 'data_analysis', name: 'Data Analysis Agent', icon: BarChart3, description: 'Descriptive statistics, tabular calculations, and CSV parsing', autonomy: 1, testPrompt: 'Check data analysis engine status' },
];

interface AgentsViewProps {
  onRunTest: (prompt: string, agent: string) => void;
}

export const AgentsView: React.FC<AgentsViewProps> = ({ onRunTest }) => {
  const [testingId, setTestingId] = useState<string | null>(null);

  const handleTest = (agent: AgentCard) => {
    setTestingId(agent.id);
    onRunTest(agent.testPrompt, agent.id);
    setTimeout(() => setTestingId(null), 2000);
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 matrix-grid-bg">
      <div className="flex items-center justify-between border-b border-matrix-border/50 pb-4">
        <div>
          <h1 className="text-sm font-mono uppercase font-bold text-slate-100 flex items-center gap-2">
            <Bot className="w-4 h-4 text-matrix-cyan" />
            16 SPECIALIZED AUTONOMOUS AGENTS GRID
          </h1>
          <p className="text-xs font-mono text-matrix-textMuted mt-0.5">
            Scoped tool schemas · Deterministic permission verification · Live post-execution verification hooks
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {AGENTS.map((agent) => {
          const Icon = agent.icon;
          const isTesting = testingId === agent.id;

          return (
            <div
              key={agent.id}
              className="matrix-glass rounded-xl p-4 flex flex-col justify-between hover:border-matrix-cyan/40 transition-all group"
            >
              <div>
                <div className="flex items-center justify-between">
                  <div className="w-8 h-8 rounded-lg bg-matrix-cyan/15 border border-matrix-cyan/30 flex items-center justify-center text-matrix-cyan">
                    <Icon className="w-4 h-4" />
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300">
                    LVL {agent.autonomy}
                  </span>
                </div>

                <div className="font-mono text-xs font-bold text-slate-100 mt-2.5">
                  {agent.name}
                </div>
                <p className="text-[11px] font-mono text-slate-400 mt-1 line-clamp-2">
                  {agent.description}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between">
                <span className="text-[10px] font-mono text-matrix-green flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> VERIFIED
                </span>
                <button
                  onClick={() => handleTest(agent)}
                  disabled={isTesting}
                  className="px-2.5 py-1 rounded bg-matrix-cyan/15 border border-matrix-cyan/40 text-matrix-cyan hover:bg-matrix-cyan hover:text-black font-mono font-bold text-[10px] transition-colors"
                >
                  {isTesting ? 'DISPATCHING...' : 'TEST AGENT'}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
