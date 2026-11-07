import React, { useState } from 'react';
import {
  MessageSquare,
  Plus,
  Send,
  Bot,
  User,
  Copy,
  Check,
  Sparkles,
} from 'lucide-react';
import { SessionItem, MessageItem } from '../../types';

interface ChatViewProps {
  sessions: SessionItem[];
  activeSessionId: string | null;
  messages: MessageItem[];
  onSelectSession: (sessionId: string) => void;
  onCreateSession: () => void;
  onSendMessage: (content: string) => void;
  loading: boolean;
}

export const ChatView: React.FC<ChatViewProps> = ({
  sessions,
  activeSessionId,
  messages,
  onSelectSession,
  onCreateSession,
  onSendMessage,
  loading,
}) => {
  const [input, setInput] = useState('');
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const handleCopy = (id: number, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="flex-1 flex h-full overflow-hidden matrix-grid-bg">
      {/* Left Session Drawer */}
      <div className="w-64 border-r border-matrix-border/60 bg-[#070B16]/90 flex flex-col">
        <div className="p-3 border-b border-matrix-border/40 flex items-center justify-between">
          <span className="text-xs font-mono uppercase text-matrix-cyan font-bold tracking-wider flex items-center gap-1.5">
            <MessageSquare className="w-3.5 h-3.5" />
            MISSIONS
          </span>
          <button
            onClick={onCreateSession}
            className="p-1.5 rounded-md bg-matrix-cyan/15 hover:bg-matrix-cyan/30 text-matrix-cyan transition-colors"
            title="Start New Mission"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {sessions.map((sess) => {
            const isActive = activeSessionId === sess.session_id;
            return (
              <button
                key={sess.session_id}
                onClick={() => onSelectSession(sess.session_id)}
                className={`w-full text-left p-2.5 rounded-lg text-xs font-mono transition-all truncate ${
                  isActive
                    ? 'bg-matrix-cyan/15 text-matrix-cyan border border-matrix-cyan/40 font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                }`}
              >
                <div className="truncate">{sess.title}</div>
                <div className="text-[10px] text-matrix-textMuted mt-0.5 truncate">
                  Agent: {sess.active_agent}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Chat Interface */}
      <div className="flex-1 flex flex-col h-full bg-[#05070E]/70">
        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500 font-mono">
              <div className="w-12 h-12 rounded-full bg-matrix-cyan/10 border border-matrix-cyan/30 flex items-center justify-center text-matrix-cyan mb-3">
                <Sparkles className="w-6 h-6 animate-pulse" />
              </div>
              <p className="text-sm text-slate-300">MATRIX Neural Interface Ready</p>
              <p className="text-xs text-matrix-textMuted mt-1 max-w-sm">
                Connected to SQLite Async persistence. Enter a directive or task request below.
              </p>
            </div>
          ) : (
            messages.map((msg) => {
              const isUser = msg.role === 'user';
              return (
                <div
                  key={msg.id}
                  className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
                >
                  <div
                    className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      isUser
                        ? 'bg-matrix-blue/20 border border-matrix-blue/40 text-matrix-blue'
                        : 'bg-matrix-cyan/20 border border-matrix-cyan/40 text-matrix-cyan'
                    }`}
                  >
                    {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </div>

                  <div
                    className={`max-w-2xl rounded-xl p-4 font-mono text-xs leading-relaxed relative group ${
                      isUser
                        ? 'bg-slate-900/90 border border-matrix-blue/30 text-slate-100'
                        : 'matrix-glass text-slate-100 shadow-[0_0_15px_rgba(0,240,255,0.05)]'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-4 mb-1.5 text-[10px] text-slate-400">
                      <span className="font-bold uppercase tracking-wider text-matrix-cyan">
                        {isUser ? 'USER' : msg.agent_name ? `AGENT: ${msg.agent_name}` : 'MATRIX CORE'}
                      </span>
                      <span>{new Date(msg.created_at).toLocaleTimeString()}</span>
                    </div>

                    <div className="whitespace-pre-wrap">{msg.content}</div>

                    <button
                      onClick={() => handleCopy(msg.id, msg.content)}
                      className="absolute top-2 right-2 p-1 rounded hover:bg-slate-800 text-slate-500 hover:text-slate-200 opacity-0 group-hover:opacity-100 transition-opacity"
                      title="Copy text"
                    >
                      {copiedId === msg.id ? (
                        <Check className="w-3.5 h-3.5 text-matrix-green" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Local Chat Input Bar */}
        <div className="p-4 border-t border-matrix-border/50 bg-[#070B16]/90">
          <form onSubmit={handleSubmit} className="flex items-center gap-2">
            <div className="relative flex-1">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type a message or command for MATRIX..."
                disabled={loading}
                className="w-full h-10 pl-4 pr-10 rounded-lg bg-slate-950/80 border border-matrix-border text-xs font-mono text-slate-100 focus:outline-none focus:border-matrix-cyan"
              />
            </div>
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="px-4 h-10 rounded-lg bg-matrix-cyan text-slate-950 hover:bg-cyan-300 disabled:opacity-40 font-mono font-bold text-xs flex items-center gap-1.5"
            >
              <Send className="w-3.5 h-3.5" />
              <span>SEND</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
