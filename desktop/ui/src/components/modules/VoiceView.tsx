import React, { useState, useRef } from 'react';
import { Mic, MicOff, Volume2, Radio, Play, Square, CheckCircle2 } from 'lucide-react';

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

  // Push-to-Talk Mic State
  const [recording, setRecording] = useState(false);
  const [transcript, setTranscript] = useState<string | null>(null);
  const [replyText, setReplyText] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

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
    } else {
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
          stream.getTracks().forEach((t) => t.stop());

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
        setStatusMsg('Listening to your microphone... Click Stop when finished.');
      } catch (err) {
        setStatusMsg('Microphone access denied by browser.');
      }
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 matrix-grid-bg">
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

        <div className="flex items-center gap-3">
          {/* Stop Speaking Button */}
          {isSpeaking && (
            <button
              onClick={onStopSpeaking}
              className="px-3 py-1.5 rounded-lg bg-matrix-red/20 border border-matrix-red text-matrix-red text-xs font-mono font-bold flex items-center gap-1.5 animate-pulse hover:bg-matrix-red/40 transition-all"
            >
              <Square className="w-3.5 h-3.5 fill-matrix-red" />
              <span>STOP SPEAKING</span>
            </button>
          )}

          <button
            onClick={onToggleVoice}
            className={`px-4 py-1.5 rounded-lg border text-xs font-mono font-bold flex items-center gap-2 transition-all ${
              voiceActive
                ? 'bg-matrix-green/20 border-matrix-green text-matrix-green shadow-[0_0_12px_rgba(0,255,157,0.3)]'
                : 'bg-slate-900 border-slate-700 text-slate-300 hover:text-white'
            }`}
          >
            <Radio className={`w-3.5 h-3.5 ${voiceActive ? 'animate-pulse' : ''}`} />
            <span>{voiceActive ? 'WAKE-WORD ARMED' : 'ARM WAKE-WORD'}</span>
          </button>
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

          <div className="p-4 rounded-lg bg-slate-950/80 border border-slate-800 text-center space-y-3">
            <button
              onClick={handleRecordToggle}
              disabled={loading}
              className={`w-16 h-16 rounded-full mx-auto flex items-center justify-center transition-all ${
                recording
                  ? 'bg-matrix-red text-white shadow-[0_0_20px_rgba(255,0,85,0.6)] animate-pulse'
                  : 'bg-matrix-cyan text-slate-950 hover:bg-cyan-300 shadow-[0_0_12px_rgba(0,240,255,0.3)]'
              }`}
            >
              {recording ? <MicOff className="w-8 h-8" /> : <Mic className="w-8 h-8" />}
            </button>
            <div className="text-xs font-mono text-slate-300 font-semibold">
              {recording ? 'Click to Stop & Process' : 'Click to Speak to MATRIX'}
            </div>
            <p className="text-[11px] font-mono text-slate-500">
              Captures your microphone audio, transcribes with Whisper, and responds via Neural TTS.
            </p>
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
