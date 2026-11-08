import React from 'react';
import {
  LayoutDashboard,
  MessageSquare,
  Mic,
  Eye,
  Bot,
  Zap,
  Globe,
  FolderGit2,
  Brain,
  Code2,
  GitBranch,
  Activity,
  Smartphone,
  PhoneCall,
  Blocks,
  Settings as SettingsIcon,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
} from 'lucide-react';
import { NavSection } from '../../types';

interface SidebarProps {
  currentSection: NavSection;
  onSelectSection: (section: NavSection) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

interface NavItem {
  id: NavSection;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: 'dashboard', label: 'Command HUD', icon: LayoutDashboard },
  { id: 'chat', label: 'Neural Chat', icon: MessageSquare, badge: 'Live' },
  { id: 'voice', label: 'JARVIS Voice', icon: Mic },
  { id: 'vision', label: 'Vision Matrix', icon: Eye },
  { id: 'agents', label: 'Agent Grid', icon: Bot, badge: '16' },
  { id: 'automation', label: 'Workflows & DAGs', icon: Zap },
  { id: 'research', label: 'Deep Research', icon: Globe },
  { id: 'files', label: 'File Intelligence', icon: FolderGit2 },
  { id: 'memory', label: 'Knowledge & RAG', icon: Brain },
  { id: 'developer', label: 'Developer Studio', icon: Code2 },
  { id: 'repositories', label: 'Repo Intelligence', icon: GitBranch, badge: '65' },
  { id: 'system', label: 'System Telemetry', icon: Activity },
  { id: 'devices', label: 'Device Sync', icon: Smartphone },
  { id: 'telephony', label: 'Phone Calling', icon: PhoneCall, badge: 'PSTN' },
  { id: 'integrations', label: 'Integrations Hub', icon: Blocks, badge: 'New' },
  { id: 'settings', label: 'System Security', icon: SettingsIcon },
];

export const Sidebar: React.FC<SidebarProps> = ({
  currentSection,
  onSelectSection,
  collapsed,
  onToggleCollapse,
}) => {
  return (
    <aside
      className={`relative flex flex-col h-full bg-[#070B16]/95 border-r border-matrix-border transition-all duration-300 select-none z-30 ${
        collapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div className="flex items-center justify-between px-3.5 h-16 border-b border-matrix-border/60">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="relative flex-shrink-0 w-8 h-8 rounded-lg bg-matrix-cyan/10 border border-matrix-cyan/40 flex items-center justify-center">
            <span className="text-matrix-cyan font-mono font-bold text-lg tracking-tighter">M</span>
            <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-matrix-cyan animate-pulse" />
          </div>
          {!collapsed && (
            <div className="flex flex-col">
              <span className="font-mono font-bold text-sm tracking-wider text-slate-100 flex items-center gap-1.5">
                MATRIX
                <span className="text-[10px] px-1 py-0.2 rounded bg-matrix-cyan/20 text-matrix-cyan border border-matrix-cyan/30">
                  v1.0
                </span>
              </span>
              <span className="text-[10px] font-mono text-matrix-textMuted tracking-tight">
                PC + ANDROID OS
              </span>
            </div>
          )}
        </div>

        <button
          onClick={onToggleCollapse}
          className="p-1.5 rounded-md hover:bg-slate-800/60 text-slate-400 hover:text-matrix-cyan transition-colors"
          title={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Navigation List */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-1">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = currentSection === item.id;

          return (
            <button
              key={item.id}
              onClick={() => onSelectSection(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-mono transition-all duration-150 group relative ${
                isActive
                  ? 'bg-matrix-cyan/15 text-matrix-cyan border border-matrix-cyan/40 shadow-[0_0_12px_rgba(0,240,255,0.15)] font-semibold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              <Icon
                className={`w-4 h-4 flex-shrink-0 transition-transform group-hover:scale-110 ${
                  isActive ? 'text-matrix-cyan' : 'text-slate-400 group-hover:text-matrix-cyan'
                }`}
              />

              {!collapsed && (
                <div className="flex items-center justify-between flex-1 truncate">
                  <span className="truncate">{item.label}</span>
                  {item.badge && (
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded-full font-mono ${
                        isActive
                          ? 'bg-matrix-cyan text-black font-bold'
                          : 'bg-slate-800 text-slate-400 border border-slate-700'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </div>
              )}

              {/* Active Indicator Bar */}
              {isActive && (
                <span className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r bg-matrix-cyan shadow-[0_0_8px_#00F0FF]" />
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom Autonomy Status */}
      {!collapsed && (
        <div className="p-3 mx-2 mb-3 rounded-lg bg-slate-900/60 border border-matrix-border/40 text-[11px] font-mono">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-matrix-amber" />
              POLICY GATE
            </span>
            <span className="text-matrix-amber font-semibold">LVL 3</span>
          </div>
          <p className="text-[10px] text-matrix-textMuted leading-tight">
            Sensors & actions monitored. High-risk execution requires explicit consent.
          </p>
        </div>
      )}
    </aside>
  );
};
