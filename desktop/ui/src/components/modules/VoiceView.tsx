import React, { useState } from 'react';
import { Mic, Volume2, Radio, Play, Sparkles, CheckCircle2 } from 'lucide-react';

interface VoiceViewProps {
  voiceActive: boolean;
  onToggleVoice: () => void;
}

export const VoiceView: React.FC<VoiceViewProps> = ({ voiceActive, onToggleVoice }) => {
  const [speakText, setSpeakText] = useState('Greetings. MATRIX Voice Subsystem is online and functional.');
  const [voiceType, setVoiceType] = useState('en-US-ChristopherNeural');
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

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

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 matrix-grid-bg">
      <div className="flex items-center justify-between border-b border-matrix-border/50 pb-4">
        <div>
          <h1 className="text-sm font-mono uppercase font-bold text-slate-100 flex items-center gap-2">
            <Mic className="w-4 h-4 text-matrix-cyan" />
            JARVIS VOICE SUBSYSTEM (ENGLISH + HINDI)
          </h1>
          <p className="text-xs font-mono text-matrix-textMuted mt-0.5">
            Realtek HD Audio · Edge-TTS Neural + SAPI5 Offline Fallback · faster-whisper INT8 STT
          </p>
        </div>
        <button
          onClick={onToggleVoice}
          className={`px-4 py-1.5 rounded-lg border text-xs font-mono font-bold flex items-center gap-2 transition-all ${
            voiceActive
              ? 'bg-matrix-green/20 border-matrix-green text-matrix-green shadow-[0_0_12px_rgba(0,255,157,0.3)]'
              : 'bg-slate-900 border-slate-700 text-slate-300 hover:text-white'
          }`}
        >
          <Radio className={`w-3.5 h-3.5 ${voiceActive ? 'animate-pulse' : ''}`} />
          <span>{voiceActive ? 'LISTENING ARMED' : 'ARM WAKE-WORD'}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* TTS Speech Synthesizer Card */}
        <div className="matrix-glass rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-mono uppercase font-bold text-slate-200 flex items-center gap-2">
              <Volume2 className="w-4 h-4 text-matrix-cyan" />
              NEURAL SPEECH GENERATOR
            </h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-matrix-cyan/20 text-matrix-cyan">
              REAL-TIME
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

          <div className="flex items-center gap-3">
            <select
              value={voiceType}
              onChange={(e) => setVoiceType(e.target.value)}
              className="px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-xs font-mono text-slate-200 focus:outline-none"
            >
              <option value="en-US-ChristopherNeural">English (US) - Christopher (Neural)</option>
              <option value="en-US-EricNeural">English (US) - Eric (Neural)</option>
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

        {/* Voice Pipeline Architecture Card */}
        <div className="matrix-glass rounded-xl p-5 space-y-4">
          <h2 className="text-xs font-mono uppercase font-bold text-slate-200 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-purple-400" />
            VOICE SUBSYSTEM PIPELINE
          </h2>

          <div className="space-y-3 text-xs font-mono">
            <div className="p-3 rounded-lg bg-slate-900/50 border border-slate-800">
              <div className="text-matrix-cyan font-bold">1. Wake-Word Detection</div>
              <p className="text-slate-400 text-[11px] mt-0.5">
                Target phrase: "Hey Matrix" · Zero cloud transmission · Real-time RMS VAD energy monitoring.
              </p>
            </div>

            <div className="p-3 rounded-lg bg-slate-900/50 border border-slate-800">
              <div className="text-matrix-blue font-bold">2. Speech-to-Text (STT)</div>
              <p className="text-slate-400 text-[11px] mt-0.5">
                faster-whisper INT8 CPU quantization · Multilingual English, Hindi, and Hinglish dictation.
              </p>
            </div>

            <div className="p-3 rounded-lg bg-slate-900/50 border border-slate-800">
              <div className="text-matrix-green font-bold">3. Text-to-Speech (TTS)</div>
              <p className="text-slate-400 text-[11px] mt-0.5">
                Neural edge-tts stream with native Windows SAPI5 offline fallback via pyttsx3.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
