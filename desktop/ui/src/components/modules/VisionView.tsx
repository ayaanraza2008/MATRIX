import React, { useState } from 'react';
import { Eye, Camera, Monitor, Upload, FileText, AlertCircle } from 'lucide-react';

export const VisionView: React.FC = () => {
  const [cameraLoading, setCameraLoading] = useState(false);
  const [screenLoading, setScreenLoading] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [cameraResult, setCameraResult] = useState<any>(null);
  const [screenResult, setScreenResult] = useState<any>(null);
  const [uploadResult, setUploadResult] = useState<any>(null);
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

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadLoading(true);
    setErrorMsg(null);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/v1/vision/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        setUploadResult(data);
      } else {
        setErrorMsg(data.detail || 'Image upload failed.');
      }
    } catch {
      setErrorMsg('Failed to upload image.');
    } finally {
      setUploadLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 matrix-grid-bg">
      <div className="flex items-center justify-between border-b border-matrix-border/50 pb-4">
        <div>
          <h1 className="text-sm font-mono uppercase font-bold text-slate-100 flex items-center gap-2">
            <Eye className="w-4 h-4 text-matrix-cyan" />
            VISION & SCENE INTELLIGENCE (NATIVE OCR + CAMERA + DESKTOP)
          </h1>
          <p className="text-xs font-mono text-matrix-textMuted mt-0.5">
            Physical Webcam (OpenCV) · Windows 11 GDI Desktop Capture · Native Windows 11 OCR Text Extraction
          </p>
        </div>

        {/* Upload Image Button */}
        <label className="cursor-pointer px-3 py-1.5 rounded-lg border border-matrix-cyan/40 bg-matrix-cyan/10 hover:bg-matrix-cyan/20 text-matrix-cyan text-xs font-mono font-bold flex items-center gap-2 transition-all">
          <Upload className="w-3.5 h-3.5" />
          <span>{uploadLoading ? 'UPLOADING...' : 'ANALYZE LOCAL IMAGE'}</span>
          <input
            type="file"
            accept="image/*"
            onChange={handleFileUpload}
            className="hidden"
            disabled={uploadLoading}
          />
        </label>
      </div>

      {errorMsg && (
        <div className="p-3 rounded-lg bg-matrix-red/15 border border-matrix-red/40 text-xs font-mono text-matrix-red flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Uploaded Image Result if present */}
      {uploadResult && (
        <div className="matrix-glass rounded-xl p-5 space-y-3 border border-matrix-cyan/40">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-mono uppercase font-bold text-matrix-cyan flex items-center gap-2">
              <FileText className="w-4 h-4" />
              UPLOADED IMAGE ANALYSIS & OCR
            </h2>
            <span className="text-[10px] font-mono text-matrix-green">PROCESSED</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-lg overflow-hidden border border-slate-800 bg-black flex items-center justify-center max-h-60">
              <img
                src={uploadResult.image_url}
                alt="Uploaded frame"
                className="max-h-60 object-contain w-full"
              />
            </div>
            <div className="space-y-2 text-xs font-mono text-slate-300">
              <div className="text-matrix-cyan font-bold">OCR Extracted Text:</div>
              <div className="p-3 rounded bg-slate-950/80 border border-slate-800 text-[11px] max-h-40 overflow-y-auto whitespace-pre-wrap">
                {uploadResult.ocr?.text || 'No text detected in this image.'}
              </div>
              <div className="text-[10px] text-slate-400">
                Sharpness: {uploadResult.analysis?.sharpness_score} · Brightness: {uploadResult.analysis?.brightness}
              </div>
            </div>
          </div>
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

          <div className="min-h-48 rounded-lg bg-slate-950/80 border border-matrix-border/60 flex items-center justify-center overflow-hidden relative">
            {cameraResult && cameraResult.image_url ? (
              <div className="w-full space-y-2 p-2">
                <img
                  src={cameraResult.image_url}
                  alt="Captured camera frame"
                  className="rounded object-contain max-h-48 w-full bg-black border border-slate-800"
                />
                <div className="text-[11px] font-mono text-slate-400 flex justify-between px-1">
                  <span>{cameraResult.width} x {cameraResult.height}</span>
                  <span className="text-matrix-green">Latency: {cameraResult.latency_ms}ms</span>
                </div>
              </div>
            ) : (
              <div className="text-center font-mono text-xs text-slate-500 space-y-1 p-6">
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
              DESKTOP SCREEN & NATIVE OCR
            </h2>
            <button
              onClick={handleCaptureScreen}
              disabled={screenLoading}
              className="px-3 py-1.5 rounded-lg bg-matrix-blue text-slate-950 font-mono font-bold text-xs hover:bg-blue-300 disabled:opacity-40 transition-colors"
            >
              {screenLoading ? 'CAPTURING...' : 'INSPECT SCREEN'}
            </button>
          </div>

          <div className="min-h-48 rounded-lg bg-slate-950/80 border border-matrix-border/60 flex items-center justify-center overflow-hidden relative">
            {screenResult && screenResult.image_url ? (
              <div className="w-full space-y-2 p-2">
                <img
                  src={screenResult.image_url}
                  alt="Desktop frame"
                  className="rounded object-contain max-h-48 w-full bg-black border border-slate-800"
                />
                <div className="text-[11px] font-mono text-slate-300 space-y-1 px-1">
                  <div className="flex justify-between text-slate-400">
                    <span>{screenResult.width} x {screenResult.height} ({screenResult.method})</span>
                    <span className="text-matrix-green">{screenResult.latency_ms}ms</span>
                  </div>
                  {screenResult.ocr?.lines?.length > 0 && (
                    <div className="p-2 rounded bg-slate-900/80 border border-slate-800 text-[10px] text-matrix-cyan max-h-20 overflow-y-auto">
                      OCR: {screenResult.ocr.lines.slice(0, 5).join(' | ')}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-center font-mono text-xs text-slate-500 space-y-1 p-6">
                <Monitor className="w-6 h-6 mx-auto opacity-40 mb-1" />
                <span>Desktop Stream Standby</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
