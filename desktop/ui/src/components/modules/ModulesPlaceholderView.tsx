import React from 'react';
import { NavSection } from '../../types';
import {
  Mic,
  Eye,
  Bot,
  Zap,
  Globe,
  FolderGit2,
  Brain,
  Code2,
  Smartphone,
  Settings as SettingsIcon,
  ShieldCheck,
  CheckCircle2,
} from 'lucide-react';

interface ModulesPlaceholderViewProps {
  section: NavSection;
  onRunAction: (cmd: string) => void;
}

const SECTION_METADATA: Record<
  string,
  {
    title: string;
    phase: string;
    desc: string;
    icon: React.ComponentType<{ className?: string }>;
    features: string[];
    actionPrompt: string;
  }
> = {
  voice: {
    title: 'JARVIS VOICE SUBSYSTEM',
    phase: 'Phase 4 Target',
    desc: 'Realtek Audio + Piper TTS + faster-whisper + openWakeWord active pipeline.',
    icon: Mic,
    features: [
      'Wake word detection ("Hey Matrix")',
      'Speech-to-text with faster-whisper (INT8 quantized)',
      'Text-to-speech with Piper / Kokoro (English + Hindi)',
      'Continuous listening and barge-in interruption',
    ],
    actionPrompt: 'Initialize audio input test on Realtek HD Audio',
  },
  vision: {
    title: 'VISION & SCREEN INTELLIGENCE',
    phase: 'Phase 9 Target',
    desc: 'Integrated Camera (VID 5986 / PID 116E) + Desktop Screenshot OCR.',
    icon: Eye,
    features: [
      'Real-time webcam frame processing via OpenCV',
      'Instant desktop screenshot OCR & UI element bounding',
      'Scene comprehension with Moondream2 / Cloud vision',
      'Explicit camera privacy shutter indicator',
    ],
    actionPrompt: 'Capture screenshot and analyze active desktop window',
  },
  agents: {
    title: '16 SPECIALIZED AGENTS GRID',
    phase: 'Phases 5-7 Multi-Agent Framework',
    desc: 'Autonomous agent ecosystem with scoped capabilities and typed schemas.',
    icon: Bot,
    features: [
      'Computer Agent (PyAutoGUI, PyWinAuto, Windows 11 controls)',
      'Browser Agent (Playwright, browser-use integration)',
      'Research & Deep Web Agent with citation generation',
      'Android Agent connected via Mobile-MCP & ADB',
    ],
    actionPrompt: 'List status of all 16 specialized agents',
  },
  automation: {
    title: 'AUTONOMOUS WORKFLOWS & DAGs',
    phase: 'Phase 7 Target',
    desc: 'Observe-Plan-Execute-Verify state machine with persistent crash recovery.',
    icon: Zap,
    features: [
      'Multi-step workflow execution engine',
      'State checkpointing in SQLite with replay protection',
      'APScheduler recurring automation triggers',
      'Configurable autonomy levels (0 to 4)',
    ],
    actionPrompt: 'View active task queue and checkpoint state',
  },
  research: {
    title: 'DEEP RESEARCH & WEB AGENT',
    phase: 'Phase 6 Target',
    desc: 'Multi-source fact extraction, contradiction resolution, and report generation.',
    icon: Globe,
    features: [
      'Parallel multi-source scraping and indexing',
      'Synthesized markdown reports with inline citations',
      'Distinction between verified facts and assumptions',
      'Offline local document fallback when internet is disabled',
    ],
    actionPrompt: 'Conduct web research on local LLM quantization',
  },
  files: {
    title: 'FILE & DOCUMENT INTELLIGENCE',
    phase: 'Phase 6 Target',
    desc: 'Multi-format document parsing (PDF, DOCX, XLSX, CSV, Code, Images).',
    icon: FolderGit2,
    features: [
      'Semantic document search over personal files',
      'Summarization and comparative extraction',
      'Strict protected directory boundaries (D:\\matrix_data)',
      'Automated spreadsheet generation and CSV manipulation',
    ],
    actionPrompt: 'Index documents in protected D:\\matrix_data storage',
  },
  memory: {
    title: 'LONG-TERM MEMORY & VECTOR RAG',
    phase: 'Phase 3 Target',
    desc: 'Structured SQLite entities + ChromaDB vector knowledge store.',
    icon: Brain,
    features: [
      'User preferences and identity preservation',
      'Project-level memory and active workspace context',
      'Embeddings via BAAI/bge-small-en-v1.5',
      'Zero fabricated memories with explicit audit log',
    ],
    actionPrompt: 'Inspect stored user memory entities in SQLite',
  },
  developer: {
    title: 'DEVELOPER STUDIO & CODING AGENT',
    phase: 'Phase 6 & 14 Target',
    desc: 'Workspace code inspection, syntax analysis, debugging, and test automation.',
    icon: Code2,
    features: [
      'Workspace repository tree inspector',
      'Sandboxed Python command runner',
      'Automated test execution (Pytest integration)',
      'Git branch and commit management via CLI',
    ],
    actionPrompt: 'Run unit test suite tests/test_foundation.py',
  },
  devices: {
    title: 'DEVICE MANAGER (PC + ANDROID SYNC)',
    phase: 'Phase 8 Target',
    desc: 'Secure device pairing protocol connecting Windows 11 PC and Android app.',
    icon: Smartphone,
    features: [
      'Cryptographic device pairing via QR code / token',
      'Remote task execution from Android to PC',
      'Bi-directional WebSocket status push',
      'Presence detection and revocation gate',
    ],
    actionPrompt: 'Generate device pairing token for Android companion',
  },
  settings: {
    title: 'SYSTEM SECURITY & GOVERNANCE',
    phase: 'Active Policy Gate (Level 3)',
    desc: 'Deterministic permission boundaries, token secrets, and tamper-evident audit.',
    icon: SettingsIcon,
    features: [
      'Level 0-4 autonomy authorization gate',
      'D:\\matrix_data storage path management',
      'Local vs Cloud fallback provider configuration',
      'Audit trail logging of every privileged command',
    ],
    actionPrompt: 'Inspect audit trail log in database',
  },
};

export const ModulesPlaceholderView: React.FC<ModulesPlaceholderViewProps> = ({
  section,
  onRunAction,
}) => {
  const meta = SECTION_METADATA[section] || {
    title: `${section.toUpperCase()} MODULE`,
    phase: 'In Roadmap',
    desc: 'Subsystem architectural specification verified in Phase 1.',
    icon: Bot,
    features: ['Modular architecture initialized in core backend'],
    actionPrompt: 'Run diagnostic health check',
  };

  const Icon = meta.icon;

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 matrix-grid-bg">
      {/* Header */}
      <div className="matrix-glass rounded-xl p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-matrix-cyan/15 border border-matrix-cyan/40 flex items-center justify-center text-matrix-cyan">
            <Icon className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-sm font-mono font-bold uppercase text-slate-100 flex items-center gap-2">
              {meta.title}
              <span className="text-[10px] px-2 py-0.5 rounded bg-matrix-cyan/20 text-matrix-cyan border border-matrix-cyan/30">
                {meta.phase}
              </span>
            </h1>
            <p className="text-xs font-mono text-matrix-textMuted mt-1">{meta.desc}</p>
          </div>
        </div>

        <button
          onClick={() => onRunAction(meta.actionPrompt)}
          className="px-4 py-2 rounded-lg bg-matrix-cyan text-slate-950 font-mono font-bold text-xs hover:bg-cyan-300 transition-colors flex items-center gap-2 self-start sm:self-auto"
        >
          <Zap className="w-3.5 h-3.5" />
          <span>TRIGGER TEST</span>
        </button>
      </div>

      {/* Target Capabilities Checklist */}
      <div className="matrix-glass rounded-xl p-6 space-y-4">
        <h2 className="text-xs font-mono uppercase tracking-wider text-matrix-cyan flex items-center gap-2">
          <ShieldCheck className="w-4 h-4" />
          ARCHITECTURAL SPECIFICATION & DELIVERABLES
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {meta.features.map((feat, idx) => (
            <div
              key={idx}
              className="p-3.5 rounded-lg bg-slate-900/60 border border-slate-800 flex items-start gap-3"
            >
              <CheckCircle2 className="w-4 h-4 text-matrix-cyan flex-shrink-0 mt-0.5" />
              <span className="text-xs font-mono text-slate-300">{feat}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
