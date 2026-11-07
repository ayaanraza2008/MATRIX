import React, { useState } from 'react';
import { Send, Mic, MicOff, Terminal, Sparkles } from 'lucide-react';

interface CommandBarProps {
  onSendCommand: (command: string, agent: string) => void;
  voiceActive: boolean;
  onToggleVoice: () => void;
  disabled?: boolean;
}

export const CommandBar: React.FC<CommandBarProps> = ({
  onSendCommand,
  voiceActive,
  onToggleVoice,
  disabled = false,
}) => {
  const [input, setInput] = useState('');
  const [selectedAgent, setSelectedAgent] = useState('core');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || disabled) return;
    onSendCommand(input.trim(), selectedAgent);
    setInput('');
  };

  return (
    <div className="relative border-t border-matrix-border/60 bg-[#070B16]/90 backdrop-blur-md p-3 z-20">
      <form onSubmit={handleSubmit} className="max-w-6xl mx-auto flex items-center gap-3">
        {/* Agent Selector Dropdown */}
        <div className="relative flex-shrink-0">
          <select
            value={selectedAgent}
            onChange={(e) => setSelectedAgent(e.target.value)}
            className="h-10 px-3 pr-8 rounded-lg bg-slate-900/90 border border-matrix-border text-xs font-mono text-matrix-cyan appearance-none cursor-pointer focus:outline-none focus:border-matrix-cyan transition-colors"
          >
            <option value="core">⚡ Core Orchestrator</option>
            <option value="computer">💻 Computer Agent</option>
            <option value="browser">🌐 Browser Agent</option>
            <option value="research">🔍 Research Agent</option>
            <option value="coding">⌨️ Coding Agent</option>
            <option value="system">📊 System Agent</option>
          </select>
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-matrix-cyan">
            <Sparkles className="w-3.5 h-3.5" />
          </div>
        </div>

        {/* Input Bar */}
        <div className="relative flex-1 flex items-center">
          <div className="absolute left-3.5 text-matrix-cyan">
            <Terminal className="w-4 h-4" />
          </div>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={disabled}
            placeholder="Direct command to MATRIX (e.g. 'Audit CPU', 'Open Browser', 'Inspect Repositories')..."
            className="w-full h-11 pl-10 pr-24 rounded-lg bg-slate-950/80 border border-matrix-border/80 focus:border-matrix-cyan text-sm font-mono text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-matrix-cyan/50 transition-all"
          />

          {/* Quick Mic Button inside input */}
          <button
            type="button"
            onClick={onToggleVoice}
            className={`absolute right-12 p-1.5 rounded-md text-xs font-mono transition-colors ${
              voiceActive
                ? 'text-matrix-green bg-matrix-green/15'
                : 'text-slate-400 hover:text-matrix-cyan'
            }`}
            title={voiceActive ? 'Disable Microphone' : 'Push to Talk'}
          >
            {voiceActive ? <Mic className="w-4 h-4 animate-pulse" /> : <MicOff className="w-4 h-4" />}
          </button>

          {/* Send Action Button */}
          <button
            type="submit"
            disabled={!input.trim() || disabled}
            className="absolute right-2 px-3 py-1.5 rounded-md bg-matrix-cyan text-slate-950 hover:bg-cyan-300 disabled:opacity-40 disabled:cursor-not-allowed font-mono font-bold text-xs flex items-center gap-1 transition-all"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
      </form>
    </div>
  );
};
