import React, { useState } from 'react';
import { Eye, Camera, Monitor, CheckCircle2 } from 'lucide-react';

export const VisionView: React.FC = () => {
  const [cameraLoading, setCameraLoading] = useState(false);
  const [screenLoading, setScreenLoading] = useState(false);
  const [cameraResult, setCameraResult] = useState<any>(null);
  const [screenResult, setScreenResult] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleCaptureCamera = async () => {
    setCameraLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch('/api/v1/vision/camera', { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        setCameraResult(data);
      } else {
        setErrorMsg(data.detail || 'Camera capture failed.');
      }
    } catch {
      setErrorMsg('Failed to connect to camera endpoint.');
    } finally {
      setCameraLoading(false);
    }
  };

  const handleCaptureScreen = async () => {
    setScreenLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch('/api/v1/vision/screenshot', { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        setScreenResult(data);
      } else {
        setErrorMsg(data.detail || 'Screenshot capture failed.');
      }
    } catch {
      setErrorMsg('Failed to connect to screenshot endpoint.');
    } finally {
      setScreenLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 matrix-grid-bg">
      <div className="flex items-center justify-between border-b border-matrix-border/50 pb-4">
        <div>
          <h1 className="text-sm font-mono uppercase font-bold text-slate-100 flex items-center gap-2">
            <Eye className="w-4 h-4 text-matrix-cyan" />
            VISION & SCENE INTELLIGENCE
          </h1>
          <p className="text-xs font-mono text-matrix-textMuted mt-0.5">
            OpenCV Integrated Camera · PyAutoGUI Desktop Screen Inspection · Optical Character Recognition
          </p>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 rounded-lg bg-matrix-red/15 border border-matrix-red/40 text-xs font-mono text-matrix-red">
          {errorMsg}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Camera Capture Card */}
        <div className="matrix-glass rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-mono uppercase font-bold text-slate-200 flex items-center gap-2">
              <Camera className="w-4 h-4 text-matrix-cyan" />
              INTEGRATED CAMERA SENSOR
            </h2>
            <button
              onClick={handleCaptureCamera}
              disabled={cameraLoading}
              className="px-3 py-1.5 rounded-lg bg-matrix-cyan text-slate-950 font-mono font-bold text-xs hover:bg-cyan-300 disabled:opacity-40 transition-colors"
            >
              {cameraLoading ? 'CAPTURING...' : 'CAPTURE FRAME'}
            </button>
          </div>

          <div className="h-48 rounded-lg bg-slate-950/80 border border-matrix-border/60 flex items-center justify-center overflow-hidden relative">
            {cameraResult ? (
              <div className="p-4 text-center font-mono text-xs text-slate-300 space-y-1">
                <CheckCircle2 className="w-8 h-8 text-matrix-green mx-auto mb-2" />
                <div className="text-matrix-cyan font-bold">FRAME CAPTURED</div>
                <div>Resolution: {cameraResult.width} x {cameraResult.height}</div>
                <div className="text-[10px] text-slate-500 truncate max-w-xs">{cameraResult.filepath}</div>
                <div className="text-[10px] text-matrix-green mt-1">Latency: {cameraResult.latency_ms} ms</div>
              </div>
            ) : (
              <div className="text-center font-mono text-xs text-slate-500 space-y-1">
                <Camera className="w-6 h-6 mx-auto opacity-40 mb-1" />
                <span>Webcam Standby (Hardware Device Index 0)</span>
              </div>
            )}
          </div>
        </div>

        {/* Desktop Screen Capture Card */}
        <div className="matrix-glass rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-mono uppercase font-bold text-slate-200 flex items-center gap-2">
              <Monitor className="w-4 h-4 text-matrix-blue" />
              DESKTOP SCREEN ANALYZER
            </h2>
            <button
              onClick={handleCaptureScreen}
              disabled={screenLoading}
              className="px-3 py-1.5 rounded-lg bg-matrix-blue text-white font-mono font-bold text-xs hover:bg-blue-600 disabled:opacity-40 transition-colors"
            >
              {screenLoading ? 'CAPTURING...' : 'CAPTURE SCREEN'}
            </button>
          </div>

          <div className="h-48 rounded-lg bg-slate-950/80 border border-matrix-border/60 flex items-center justify-center overflow-hidden relative">
            {screenResult ? (
              <div className="p-4 text-center font-mono text-xs text-slate-300 space-y-1">
                <CheckCircle2 className="w-8 h-8 text-matrix-green mx-auto mb-2" />
                <div className="text-matrix-blue font-bold">SCREENSHOT ANALYZED</div>
                <div>Resolution: {screenResult.width} x {screenResult.height}</div>
                <div className="text-[10px] text-slate-500 truncate max-w-xs">{screenResult.filepath}</div>
                <div className="text-[10px] text-matrix-cyan mt-1">Verified: Saved to D:\matrix_data\cache\vision</div>
              </div>
            ) : (
              <div className="text-center font-mono text-xs text-slate-500 space-y-1">
                <Monitor className="w-6 h-6 mx-auto opacity-40 mb-1" />
                <span>Desktop Screen Visual Capture Ready</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
