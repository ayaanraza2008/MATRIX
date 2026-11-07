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
  HealthData,
  LiveMetricsData,
  SystemInfoData,
  CapabilityItem,
  SessionItem,
  MessageItem,
  HologramState,
  NavSection,
  HandsFreeMode,
} from './types';

export const App: React.FC = () => {
  // Navigation
  const [currentSection, setCurrentSection] = useState<NavSection>('dashboard');
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);

  // System & Connection State
  const [connected, setConnected] = useState<boolean>(false);
  const [health, setHealth] = useState<HealthData | null>(null);
  const [metrics, setMetrics] = useState<LiveMetricsData | null>(null);
  const [systemInfo, setSystemInfo] = useState<SystemInfoData | null>(null);
  const [capabilities, setCapabilities] = useState<CapabilityItem[] | null>(null);

  // Hologram & Voice State
  const [hologramState, setHologramState] = useState<HologramState>('idle');
  const [voiceActive, setVoiceActive] = useState<boolean>(false);
  const [audioMuted, setAudioMuted] = useState<boolean>(false);
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const [audioPlayer, setAudioPlayer] = useState<HTMLAudioElement | null>(null);
  const [handsFreeMode, setHandsFreeMode] = useState<HandsFreeMode>('continuous');
  const [lastTranscript, setLastTranscript] = useState<string>('');
  const [lastResponse, setLastResponse] = useState<string>('');

  // Audio Recording (Push-to-Talk)
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // Conversational Data
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [chatLoading, setChatLoading] = useState<boolean>(false);

  // WebSocket & Timeout Refs
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  // 1. Fetch Health & Telemetry
  const fetchHealthAndMetrics = useCallback(async () => {
    try {
      const [hRes, mRes, infoRes, capsRes] = await Promise.all([
        fetch('/api/v1/health').catch(() => null),
        fetch('/api/v1/system/metrics').catch(() => null),
        fetch('/api/v1/system/info').catch(() => null),
        fetch('/api/v1/capabilities').catch(() => null),
      ]);

      if (hRes && hRes.ok) {
        const hData = await hRes.json();
        setHealth(hData);
        setConnected(hData.status === 'OK');
      }

      if (mRes && mRes.ok) {
        const mData = await mRes.json();
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
          if (data.type === 'WAKE_WORD_DETECTED') {
            setHologramState('wake_word');
          } else if (data.type === 'RECORDING_STARTED') {
            setHologramState('listening');
            setIsRecording(true);
          } else if (data.type === 'RECORDING_STOPPED') {
            setHologramState('processing');
            setIsRecording(false);
          } else if (data.type === 'TRANSCRIPT_GENERATED') {
            if (data.data?.text) setLastTranscript(data.data.text);
            setHologramState('thinking');
          } else if (data.type === 'THINKING') {
            setHologramState('thinking');
          } else if (data.type === 'AGENT_SELECTED') {
            setHologramState('processing');
          } else if (data.type === 'TASK_PROGRESS') {
            setHologramState('executing');
          } else if (data.type === 'TTS_STARTED') {
            setHologramState('speaking');
            setIsSpeaking(true);
            if (data.data?.text) setLastResponse(data.data.text);
            if (data.data?.audio_url && !audioMuted) {
              const audio = new Audio(data.data.audio_url);
              setAudioPlayer(audio);
              audio.play().catch(() => {});
              audio.onended = () => {
                setIsSpeaking(false);
                setHologramState(handsFreeMode === 'continuous' ? 'listening' : 'idle');
              };
            }
          } else if (data.type === 'TTS_FINISHED') {
            setIsSpeaking(false);
            setHologramState(handsFreeMode === 'continuous' ? 'listening' : 'idle');
          } else if (data.type === 'INTERRUPTED') {
            setIsSpeaking(false);
            setHologramState('interrupted');
          } else if (data.type === 'LISTENING_RESUMED') {
            setHologramState('idle');
          } else if (data.type === 'MODE_CHANGED' && data.data?.mode) {
            setHandsFreeMode(data.data.mode);
          }
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
        reconnectTimeoutRef.current = window.setTimeout(() => {
          connectWebSocket();
        }, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      // Reconnect after delay
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

  // 4. Speech Synthesis Playback Helper
  const playSpeech = async (text: string) => {
    try {
      setHologramState('speaking');
      setIsSpeaking(true);
      const res = await fetch('/api/v1/voice/speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        setAudioPlayer(audio);
        audio.onended = () => {
          setHologramState('idle');
          setIsSpeaking(false);
        };
        audio.onerror = () => {
          setHologramState('idle');
          setIsSpeaking(false);
        };
        await audio.play();
      } else {
        setHologramState('idle');
        setIsSpeaking(false);
      }
    } catch {
      setHologramState('idle');
      setIsSpeaking(false);
    }
  };

  const handleStopSpeaking = async () => {
    if (audioPlayer) {
      audioPlayer.pause();
      audioPlayer.currentTime = 0;
    }
    setIsSpeaking(false);
    setHologramState('idle');
    try {
      await fetch('/api/v1/voice/stop', { method: 'POST' });
    } catch {
      // ignore
    }
  };

  // 5. Genuine Command & Interaction Dispatch
  const handleSendCommand = async (commandText: string, agent: string = 'core') => {
    if (!activeSessionId) return;

    setChatLoading(true);
    setHologramState('thinking');

    // Optimistically append user message
    const tempUserMsg: MessageItem = {
      id: Date.now(),
      session_id: activeSessionId,
      role: 'user',
      content: commandText,
      agent_name: agent,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      // Call genuine MATRIX Brain interaction endpoint
      const res = await fetch(`/api/v1/sessions/${activeSessionId}/interact`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          role: 'user',
          content: commandText,
          agent_name: agent,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        const assistantMsg: MessageItem = {
          id: Date.now() + 1,
          session_id: activeSessionId,
          role: 'assistant',
          content: data.reply,
          agent_name: agent,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);

        // Synthesize audio response if unmuted
        if (!audioMuted && data.reply) {
          playSpeech(data.reply);
        } else {
          setHologramState('idle');
        }
      } else {
        setHologramState('error');
        setTimeout(() => setHologramState('idle'), 2000);
      }
    } catch {
      setHologramState('error');
      setTimeout(() => setHologramState('idle'), 2000);
    } finally {
      setChatLoading(false);
    }
  };

  // 6. Real Microphone Voice Recording & Chat
  const handleToggleVoice = async () => {
    if (isRecording) {
      // Stop active recording and transmit
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      setIsRecording(false);
      setVoiceActive(false);
      setHologramState('thinking');
    } else {
      // Request mic permission and start recording
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;
        audioChunksRef.current = [];

        mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) audioChunksRef.current.push(e.data);
        };

        mediaRecorder.onstop = async () => {
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          stream.getTracks().forEach((track) => track.stop());

          if (audioBlob.size > 0) {
            setChatLoading(true);
            setHologramState('thinking');
            const formData = new FormData();
            formData.append('file', audioBlob, 'mic.webm');
            formData.append('session_id', activeSessionId || 'sess_default');

            try {
              const res = await fetch('/api/v1/voice/chat-voice', {
                method: 'POST',
                body: formData,
              });
              const data = await res.json();
              if (res.ok && data.user_text) {
                const uMsg: MessageItem = {
                  id: Date.now(),
                  session_id: activeSessionId || 'sess_default',
                  role: 'user',
                  content: data.user_text,
                  agent_name: 'voice',
                  created_at: new Date().toISOString(),
                };
                const aMsg: MessageItem = {
                  id: Date.now() + 1,
                  session_id: activeSessionId || 'sess_default',
                  role: 'assistant',
                  content: data.reply_text,
                  agent_name: 'voice',
                  created_at: new Date().toISOString(),
                };
                setMessages((prev) => [...prev, uMsg, aMsg]);

                if (data.audio_url && !audioMuted) {
                  setHologramState('speaking');
                  setIsSpeaking(true);
                  const audio = new Audio(data.audio_url);
                  setAudioPlayer(audio);
                  audio.onended = () => {
                    setHologramState('idle');
                    setIsSpeaking(false);
                  };
                  audio.onerror = () => {
                    setHologramState('idle');
                    setIsSpeaking(false);
                  };
                  await audio.play();
                } else {
                  setHologramState('idle');
                }
              }
            } catch {
              setHologramState('error');
              setTimeout(() => setHologramState('idle'), 2000);
            } finally {
              setChatLoading(false);
            }
          }
        };

        mediaRecorder.start();
        setIsRecording(true);
        setVoiceActive(true);
        setHologramState('listening');
      } catch (err) {
        console.error('Microphone access denied:', err);
        setHologramState('error');
        setTimeout(() => setHologramState('idle'), 2000);
      }
    }
  };

  const handleSetHandsFreeMode = async (mode: HandsFreeMode) => {
    setHandsFreeMode(mode);
    try {
      await fetch('/api/v1/voice/hands-free/mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode }),
      });
    } catch {}
  };

  const handleToggleMute = () => {
    setAudioMuted((prev) => !prev);
    if (!audioMuted && isSpeaking) {
      handleStopSpeaking();
    }
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
          isSpeaking={isSpeaking}
          onStopSpeaking={handleStopSpeaking}
        />

        {/* Dynamic Section Content */}
        <main className="flex-1 overflow-hidden flex flex-col relative">
          {currentSection === 'dashboard' && (
            <DashboardView
              health={health}
              metrics={metrics}
              hologramState={hologramState}
              capabilities={capabilities || []}
              lastTranscript={lastTranscript}
              lastResponse={lastResponse}
              isSpeaking={isSpeaking}
              onStopSpeaking={handleStopSpeaking}
              handsFreeMode={handsFreeMode}
              onChangeMode={handleSetHandsFreeMode}
              onToggleListen={handleToggleVoice}
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
              isSpeaking={isSpeaking}
              onStopSpeaking={handleStopSpeaking}
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
