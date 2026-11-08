import React, { useState, useEffect, useRef } from 'react';
import {
  Mic,
  MicOff,
  Volume2,
  Radio,
  Play,
  Square,
  CheckCircle2,
  AlertCircle,
  ShieldAlert,
  Activity
} from 'lucide-react';

interface VoiceViewProps {
  voiceActive: boolean;
  onToggleVoice: () => void;
  isSpeaking?: boolean;
  onStopSpeaking?: () => void;
}

export const VoiceView: React.FC<VoiceViewProps> = ({
  voiceActive,
  onToggleVoice,
  isSpeaking = false,
  onStopSpeaking,
}) => {
  const [speakText, setSpeakText] = useState('Greetings. MATRIX Voice Subsystem is online and functional.');
  const [voiceType, setVoiceType] = useState('en-US-ChristopherNeural');
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  // Push-to-Talk & Real-Time Audio State
  const [recording, setRecording] = useState(false);
  const [transcript, setTranscript] = useState<string | null>(null);
  const [replyText, setReplyText] = useState<string | null>(null);
  const [micPermission, setMicPermission] = useState<'prompt' | 'granted' | 'denied'>('prompt');
  const [audioDevices, setAudioDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedAudioDeviceId, setSelectedAudioDeviceId] = useState<string>('');
  const [audioLevel, setAudioLevel] = useState<number>(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const activeStreamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    checkMicPermission();
    enumerateAudioDevices();

    return () => {
      cleanupAudioContext();
    };
  }, []);

  const checkMicPermission = async () => {
    try {
      if (navigator.permissions && navigator.permissions.query) {
        const res = await navigator.permissions.query({ name: 'microphone' as any });
        setMicPermission(res.state as any);
        res.onchange = () => {
          setMicPermission(res.state as any);
          if (res.state === 'granted') {
            enumerateAudioDevices();
          }
        };
      }
    } catch {
      // Unimplemented in some browsers
    }
  };

  const enumerateAudioDevices = async () => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
      const devices = await navigator.mediaDevices.enumerateDevices();
      const audioInputs = devices.filter((d) => d.kind === 'audioinput');
      setAudioDevices(audioInputs);
      if (audioInputs.length > 0 && !selectedAudioDeviceId) {
        setSelectedAudioDeviceId(audioInputs[0].deviceId);
      }
    } catch (e) {
      console.warn('Failed to enumerate audio devices:', e);
    }
  };

  const cleanupAudioContext = () => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    if (activeStreamRef.current) {
      activeStreamRef.current.getTracks().forEach((t) => t.stop());
      activeStreamRef.current = null;
    }
    setAudioLevel(0);
  };

  const startAudioMonitoring = (stream: MediaStream) => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      const audioCtx = new AudioCtx();
      audioContextRef.current = audioCtx;

      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      analyserRef.current = analyser;

      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      const updateMeter = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);

        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          sum += dataArray[i];
        }
        const avg = sum / bufferLength;
        const normalized = Math.min(100, Math.round((avg / 128) * 100));
        setAudioLevel(normalized);

        animationFrameRef.current = requestAnimationFrame(updateMeter);
      };

      updateMeter();
    } catch (e) {
      console.warn('Web Audio meter initialization failed:', e);
    }
  };

  const handleSynthesize = async () => {
    if (!speakText.trim()) return;
    setLoading(true);
    setStatusMsg(null);
    try {
      const res = await fetch('/api/v1/voice/speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: speakText, voice: voiceType }),
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        setAudioUrl(url);
        setStatusMsg('Speech synthesized successfully.');
      } else {
        setStatusMsg('Speech synthesis failed.');
      }
    } catch {
      setStatusMsg('Network error connecting to voice engine.');
    } finally {
      setLoading(false);
    }
  };

  const handleRecordToggle = async () => {
    if (recording) {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      setRecording(false);
      cleanupAudioContext();
    } else {
      try {
        const constraints = {
          audio: selectedAudioDeviceId ? { deviceId: { exact: selectedAudioDeviceId } } : true,
        };
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        activeStreamRef.current = stream;
        setMicPermission('granted');

        startAudioMonitoring(stream);

        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;
        audioChunksRef.current = [];

        mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) audioChunksRef.current.push(e.data);
        };

        mediaRecorder.onstop = async () => {
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          cleanupAudioContext();

          if (audioBlob.size > 0) {
            setLoading(true);
            setStatusMsg('Transcribing and processing speech...');
            const formData = new FormData();
            formData.append('file', audioBlob, 'mic.webm');
            formData.append('session_id', 'sess_voice_ui');

            try {
              const res = await fetch('/api/v1/voice/chat-voice', {
                method: 'POST',
                body: formData,
              });
              const data = await res.json();
              if (res.ok && data.user_text) {
                setTranscript(data.user_text);
                setReplyText(data.reply_text);
                setStatusMsg('Voice loop executed successfully.');
                if (data.audio_url) {
                  setAudioUrl(data.audio_url);
                  const a = new Audio(data.audio_url);
                  a.play();
                }
              } else {
                setStatusMsg(data.error || 'No speech recognized.');
              }
            } catch {
              setStatusMsg('Network error during voice transmission.');
            } finally {
              setLoading(false);
            }
          }
        };

        mediaRecorder.start();
        setRecording(true);
        setStatusMsg('Listening to your microphone... Speak now and click Stop when done.');
      } catch (err: any) {
        setMicPermission('denied');
        setStatusMsg(`Microphone access error: ${err.message || 'Permission denied by browser'}`);
      }
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 matrix-grid-bg">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-matrix-border/50 pb-4">
        <div>
          <h1 className="text-sm font-mono uppercase font-bold text-slate-100 flex items-center gap-2">
            <Mic className="w-4 h-4 text-matrix-cyan" />
            JARVIS VOICE SUBSYSTEM (ENGLISH + HINDI + HINGLISH)
          </h1>
          <p className="text-xs font-mono text-matrix-textMuted mt-0.5">
            Realtek HD Audio · Edge-TTS Neural Christopher/Swara/Prabhat · faster-whisper INT8 STT
          </p>
        </div>

        {/* Global Interruption & Wake-Word Switch */}
        <div className="flex items-center gap-3">
          {isSpeaking && (
            <button
              onClick={onStopSpeaking}
              className="px-3 py-1.5 rounded-lg bg-matrix-red text-white text-xs font-mono font-bold flex items-center gap-1.5 animate-pulse shadow-md shadow-matrix-red/30 hover:bg-red-600 transition-all"
            >
              <Square className="w-3.5 h-3.5 fill-white" />
              <span>BARGE-IN / SILENCE</span>
            </button>
          )}

          <button
            onClick={onToggleVoice}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold flex items-center gap-1.5 transition-all ${
              voiceActive
                ? 'bg-matrix-green text-slate-950 shadow-md shadow-matrix-green/20'
                : 'bg-slate-900 border border-slate-700 text-slate-400 hover:text-slate-200'
            }`}
          >
            <Radio className={`w-3.5 h-3.5 ${voiceActive ? 'animate-pulse' : ''}`} />
            <span>{voiceActive ? 'WAKE-WORD ARMED' : 'ARM WAKE-WORD'}</span>
          </button>
        </div>
      </div>

      {/* Microphone Permission and Device Status Bar */}
      <div className="flex flex-wrap items-center justify-between p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs font-mono gap-3">
        <div className="flex items-center gap-3">
          <span className="text-slate-400">MICROPHONE PERMISSION:</span>
          {micPermission === 'granted' ? (
            <span className="px-2 py-0.5 rounded bg-matrix-green/10 border border-matrix-green/40 text-matrix-green flex items-center gap-1.5 font-bold">
              <CheckCircle2 className="w-3.5 h-3.5" /> GRANTED
            </span>
          ) : micPermission === 'denied' ? (
            <span className="px-2 py-0.5 rounded bg-matrix-red/10 border border-matrix-red/40 text-matrix-red flex items-center gap-1.5 font-bold">
              <ShieldAlert className="w-3.5 h-3.5" /> DENIED (Browser Blocked)
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/40 text-amber-400 flex items-center gap-1.5 font-bold">
              <AlertCircle className="w-3.5 h-3.5" /> PROMPT / NOT REQUESTED
            </span>
          )}

          {/* Device Selector */}
          {audioDevices.length > 0 && (
            <div className="flex items-center gap-2 ml-4">
              <span className="text-slate-400">DEVICE:</span>
              <select
                value={selectedAudioDeviceId}
                onChange={(e) => setSelectedAudioDeviceId(e.target.value)}
                className="bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-200 text-[11px]"
              >
                {audioDevices.map((d, idx) => (
                  <option key={d.deviceId || idx} value={d.deviceId}>
                    {d.label || `Microphone ${idx + 1}`}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Live Audio Level dB Meter */}
        <div className="flex items-center gap-2">
          <span className="text-slate-400 flex items-center gap-1 text-[11px]">
            <Activity className="w-3.5 h-3.5 text-matrix-cyan" />
            MIC LEVEL:
          </span>
          <div className="w-32 h-3 bg-slate-950 rounded-full overflow-hidden border border-slate-800 flex items-center p-0.5">
            <div
              className="h-full rounded-full transition-all duration-75"
              style={{
                width: `${audioLevel}%`,
                backgroundColor: audioLevel > 70 ? '#ff0055' : audioLevel > 30 ? '#00f0ff' : '#00ff66',
                boxShadow: audioLevel > 20 ? '0 0 8px currentColor' : 'none'
              }}
            />
          </div>
          <span className="text-[10px] text-slate-400 w-8 text-right">{audioLevel}%</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Push-to-Talk Speech & Conversation Loop */}
        <div className="matrix-glass rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-mono uppercase font-bold text-slate-200 flex items-center gap-2">
              <Mic className="w-4 h-4 text-matrix-green" />
              MICROPHONE SPEECH-TO-SPEECH INTERFACE
            </h2>
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${
              recording ? 'bg-matrix-red/20 text-matrix-red animate-pulse' : 'bg-matrix-green/20 text-matrix-green'
            }`}>
              {recording ? 'RECORDING' : 'STANDBY'}
            </span>
          </div>

          <div className="p-5 rounded-lg bg-slate-950/80 border border-slate-800 text-center space-y-4">
            <button
              onClick={handleRecordToggle}
              disabled={loading}
              className={`w-20 h-20 rounded-full mx-auto flex items-center justify-center transition-all ${
                recording
                  ? 'bg-matrix-red text-white shadow-[0_0_24px_rgba(255,0,85,0.7)] animate-pulse'
                  : 'bg-matrix-cyan text-slate-950 hover:bg-cyan-300 shadow-[0_0_16px_rgba(0,240,255,0.4)]'
              }`}
            >
              {recording ? <MicOff className="w-10 h-10" /> : <Mic className="w-10 h-10" />}
            </button>
            <div className="text-xs font-mono text-slate-200 font-bold">
              {recording ? 'Listening... Click to Stop & Process' : 'Click to Speak to MATRIX'}
            </div>
            <p className="text-[11px] font-mono text-slate-400 max-w-sm mx-auto">
              Directly commands your Windows 11 desktop: launch apps, alter volume, open websites, create folders, or converse naturally.
            </p>

            {/* In-Card Dynamic VU Waveform Bars */}
            {recording && (
              <div className="flex items-center justify-center gap-1 pt-2 h-8">
                {[...Array(16)].map((_, i) => {
                  const factor = Math.sin((i / 16) * Math.PI);
                  const barHeight = Math.max(4, Math.round(audioLevel * factor * 0.3));
                  return (
                    <div
                      key={i}
                      className="w-1.5 rounded-full bg-matrix-cyan transition-all duration-75"
                      style={{ height: `${barHeight}px` }}
                    />
                  );
                })}
              </div>
            )}
          </div>

          {transcript && (
            <div className="space-y-2 text-xs font-mono">
              <div className="p-3 rounded-lg bg-slate-900/70 border border-slate-800">
                <span className="text-slate-400 font-bold">You Said: </span>
                <span className="text-slate-200">"{transcript}"</span>
              </div>
              {replyText && (
                <div className="p-3 rounded-lg bg-matrix-cyan/10 border border-matrix-cyan/30 text-matrix-cyan">
                  <span className="font-bold">MATRIX: </span>
                  <span>{replyText}</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* TTS Speech Synthesizer Card */}
        <div className="matrix-glass rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-mono uppercase font-bold text-slate-200 flex items-center gap-2">
              <Volume2 className="w-4 h-4 text-matrix-cyan" />
              NEURAL SPEECH GENERATOR
            </h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-matrix-cyan/20 text-matrix-cyan">
              DIRECT TTS
            </span>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-mono text-slate-400">Speech Phrase</label>
            <textarea
              value={speakText}
              onChange={(e) => setSpeakText(e.target.value)}
              rows={3}
              className="w-full p-3 rounded-lg bg-slate-950/80 border border-matrix-border text-xs font-mono text-slate-100 focus:outline-none focus:border-matrix-cyan"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <select
              value={voiceType}
              onChange={(e) => setVoiceType(e.target.value)}
              className="px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-xs font-mono text-slate-200 focus:outline-none"
            >
              <option value="en-US-ChristopherNeural">English (US) - Christopher (JARVIS)</option>
              <option value="en-IN-PrabhatNeural">Hinglish (India) - Prabhat (Neural)</option>
              <option value="hi-IN-SwaraNeural">Hindi (India) - Swara (Neural)</option>
              <option value="hi-IN-MadhurNeural">Hindi (India) - Madhur (Neural)</option>
            </select>

            <button
              onClick={handleSynthesize}
              disabled={loading}
              className="px-4 py-2 rounded-lg bg-matrix-cyan text-slate-950 font-mono font-bold text-xs hover:bg-cyan-300 disabled:opacity-40 transition-colors flex items-center gap-1.5"
            >
              <Play className="w-3.5 h-3.5" />
              <span>{loading ? 'SYNTHESIZING...' : 'SPEAK NOW'}</span>
            </button>
          </div>

          {statusMsg && (
            <p className="text-xs font-mono text-matrix-cyan mt-1 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" />
              {statusMsg}
            </p>
          )}

          {audioUrl && (
            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
              <audio controls src={audioUrl} autoPlay className="w-full h-8" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
