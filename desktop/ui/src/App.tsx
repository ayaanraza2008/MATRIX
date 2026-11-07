import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Sidebar } from './components/layout/Sidebar';
import { TopNavbar } from './components/layout/TopNavbar';
import { CommandBar } from './components/layout/CommandBar';
import { DashboardView } from './components/modules/DashboardView';
import { ChatView } from './components/modules/ChatView';
import { SystemMonitorView } from './components/modules/SystemMonitorView';
import { RepoIntelligenceView } from './components/modules/RepoIntelligenceView';
import { VoiceView } from './components/modules/VoiceView';
import { VisionView } from './components/modules/VisionView';
import { AgentsView } from './components/modules/AgentsView';
import { AutomationView } from './components/modules/AutomationView';
import { ResearchView } from './components/modules/ResearchView';
import { FilesView } from './components/modules/FilesView';
import { MemoryView } from './components/modules/MemoryView';
import { DeveloperStudioView } from './components/modules/DeveloperStudioView';
import { DevicesView } from './components/modules/DevicesView';
import { SettingsView } from './components/modules/SettingsView';

import {
  NavSection,
  HologramState,
  HealthData,
  LiveMetricsData,
  SystemInfoData,
  CapabilityItem,
  SessionItem,
  MessageItem,
} from './types';

export const App: React.FC = () => {
  const [currentSection, setCurrentSection] = useState<NavSection>('dashboard');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Connectivity & Telemetry State
  const [connected, setConnected] = useState(false);
  const [health, setHealth] = useState<HealthData | null>(null);
  const [metrics, setMetrics] = useState<LiveMetricsData | null>(null);
  const [systemInfo, setSystemInfo] = useState<SystemInfoData | null>(null);
  const [capabilities, setCapabilities] = useState<CapabilityItem[]>([]);
  const [hologramState, setHologramState] = useState<HologramState>('idle');

  // Voice & Audio Controls
  const [voiceActive, setVoiceActive] = useState(false);
  const [audioMuted, setAudioMuted] = useState(false);

  // Chat Sessions & Messages State
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [chatLoading, setChatLoading] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  // 1. Fetch Initial Telemetries & Health via REST
  const fetchHealthAndMetrics = useCallback(async () => {
    try {
      const [healthRes, metricsRes, infoRes, capsRes] = await Promise.all([
        fetch('/api/v1/health').catch(() => null),
        fetch('/api/v1/system/metrics').catch(() => null),
        fetch('/api/v1/system/info').catch(() => null),
        fetch('/api/v1/capabilities').catch(() => null),
      ]);

      if (healthRes && healthRes.ok) {
        const hData = await healthRes.json();
        setHealth(hData);
        setConnected(true);
      } else {
        setConnected(false);
        setHologramState('offline');
      }

      if (metricsRes && metricsRes.ok) {
        const mData = await metricsRes.json();
        setMetrics(mData);
      }

      if (infoRes && infoRes.ok) {
        const iData = await infoRes.json();
        setSystemInfo(iData);
      }

      if (capsRes && capsRes.ok) {
        const cData = await capsRes.json();
        setCapabilities(cData);
      }
    } catch {
      setConnected(false);
      setHologramState('offline');
    }
  }, []);

  // 2. Fetch Sessions & Active Messages
  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/sessions');
      if (res.ok) {
        const data: SessionItem[] = await res.json();
        setSessions(data);
        if (data.length > 0 && !activeSessionId) {
          setActiveSessionId(data[0].session_id);
        } else if (data.length === 0) {
          // Auto create initial session
          createSession();
        }
      }
    } catch {
      // Offline fallback
    }
  }, [activeSessionId]);

  const fetchMessages = useCallback(async (sessionId: string) => {
    try {
      const res = await fetch(`/api/v1/sessions/${sessionId}/messages`);
      if (res.ok) {
        const data: MessageItem[] = await res.json();
        setMessages(data);
      }
    } catch {
      // Offline fallback
    }
  }, []);

  const createSession = async () => {
    try {
      const res = await fetch('/api/v1/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'New Mission Directive', active_agent: 'core' }),
      });
      if (res.ok) {
        const newSess: SessionItem = await res.json();
        setSessions((prev) => [newSess, ...prev]);
        setActiveSessionId(newSess.session_id);
        setMessages([]);
      }
    } catch {
      // Offline fallback
    }
  };

  useEffect(() => {
    if (activeSessionId) {
      fetchMessages(activeSessionId);
    }
  }, [activeSessionId, fetchMessages]);

  // 3. Connect Real-time WebSocket
  const connectWebSocket = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/events`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setHologramState('idle');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'telemetry_update' && data.payload) {
            setMetrics((prev) => ({
              cpu: {
                percent: data.payload.cpu_percent,
                frequency_mhz: prev?.cpu?.frequency_mhz ?? 0,
              },
              memory: {
                percent: data.payload.ram_percent,
                used_mb: data.payload.ram_used_mb,
                available_mb: data.payload.ram_available_mb,
                total_mb: prev?.memory?.total_mb ?? 8000,
              },
              status: data.payload.status,
            }));
          }
        } catch {
          // Ignore invalid JSON frame
        }
      };

      ws.onclose = () => {
        setConnected(false);
        setHologramState('offline');
        // Exponential backoff reconnect
        reconnectTimeoutRef.current = window.setTimeout(() => {
          connectWebSocket();
        }, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      // Reconnect after delay
      reconnectTimeoutRef.current = window.setTimeout(() => {
        connectWebSocket();
      }, 3000);
    }
  }, []);

  useEffect(() => {
    fetchHealthAndMetrics();
    fetchSessions();
    connectWebSocket();

    const pollInterval = window.setInterval(fetchHealthAndMetrics, 4000);

    return () => {
      clearInterval(pollInterval);
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    };
  }, [fetchHealthAndMetrics, fetchSessions, connectWebSocket]);

  // 4. Command Dispatch Logic
  const handleSendCommand = async (commandText: string, agent: string = 'core') => {
    if (!activeSessionId) return;

    setChatLoading(true);
    setHologramState('thinking');

    try {
      // 1. Post user message to backend
      const res = await fetch(`/api/v1/sessions/${activeSessionId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          role: 'user',
          content: commandText,
          agent_name: agent,
        }),
      });

      if (res.ok) {
        const userMsg: MessageItem = await res.json();
        setMessages((prev) => [...prev, userMsg]);

        // Simulate core response for Phase 1 verification
        setHologramState('executing');
        setTimeout(async () => {
          const replyRes = await fetch(`/api/v1/sessions/${activeSessionId}/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              role: 'assistant',
              content: `MATRIX received directive: "${commandText}". Command verified under Policy Level 3. Execution telemetry logged to SQLite.`,
              agent_name: agent,
            }),
          });
          if (replyRes.ok) {
            const assistantMsg: MessageItem = await replyRes.json();
            setMessages((prev) => [...prev, assistantMsg]);
          }
          setHologramState('idle');
          setChatLoading(false);
        }, 600);
      }
    } catch {
      setHologramState('error');
      setChatLoading(false);
      setTimeout(() => setHologramState('idle'), 2000);
    }
  };

  const handleToggleVoice = () => {
    setVoiceActive((prev) => {
      const next = !prev;
      setHologramState(next ? 'listening' : 'idle');
      return next;
    });
  };

  const handleToggleMute = () => {
    setAudioMuted((prev) => !prev);
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#05070E] text-slate-100 font-sans">
      {/* Navigation Sidebar */}
      <Sidebar
        currentSection={currentSection}
        onSelectSection={setCurrentSection}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((p) => !p)}
      />

      {/* Main Command Workspace */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Top Navbar */}
        <TopNavbar
          connected={connected}
          health={health}
          metrics={metrics}
          voiceActive={voiceActive}
          onToggleVoice={handleToggleVoice}
          audioMuted={audioMuted}
          onToggleMute={handleToggleMute}
        />

        {/* Dynamic Section Content */}
        <main className="flex-1 overflow-hidden flex flex-col relative">
          {currentSection === 'dashboard' && (
            <DashboardView
              health={health}
              metrics={metrics}
              hologramState={hologramState}
              capabilities={capabilities}
              onQuickAction={(cmd) => {
                setCurrentSection('chat');
                handleSendCommand(cmd);
              }}
            />
          )}

          {currentSection === 'chat' && (
            <ChatView
              sessions={sessions}
              activeSessionId={activeSessionId}
              messages={messages}
              onSelectSession={setActiveSessionId}
              onCreateSession={createSession}
              onSendMessage={handleSendCommand}
              loading={chatLoading}
            />
          )}

          {currentSection === 'system' && (
            <SystemMonitorView
              health={health}
              metrics={metrics}
              systemInfo={systemInfo}
            />
          )}

          {currentSection === 'repositories' && <RepoIntelligenceView />}

          {currentSection === 'voice' && (
            <VoiceView
              voiceActive={voiceActive}
              onToggleVoice={handleToggleVoice}
            />
          )}

          {currentSection === 'vision' && <VisionView />}

          {currentSection === 'agents' && (
            <AgentsView
              onRunTest={(prompt, agent) => {
                setCurrentSection('chat');
                handleSendCommand(prompt, agent);
              }}
            />
          )}

          {currentSection === 'automation' && <AutomationView />}

          {currentSection === 'research' && <ResearchView />}

          {currentSection === 'files' && <FilesView />}

          {currentSection === 'memory' && <MemoryView />}

          {currentSection === 'developer' && <DeveloperStudioView />}

          {currentSection === 'devices' && <DevicesView />}

          {currentSection === 'settings' && <SettingsView />}
        </main>

        {/* Persistent Bottom Command Input */}
        <CommandBar
          onSendCommand={handleSendCommand}
          voiceActive={voiceActive}
          onToggleVoice={handleToggleVoice}
          disabled={chatLoading}
        />
      </div>
    </div>
  );
};

export default App;
