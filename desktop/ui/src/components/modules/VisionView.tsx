import React, { useState, useEffect, useRef } from 'react';
import {
  Eye,
  Camera,
  Monitor,
  Upload,
  FileText,
  AlertCircle,
  Hand,
  CheckCircle2,
  Video,
  VideoOff,
  ShieldAlert
} from 'lucide-react';
import { AirTouchStudio } from './AirTouchStudio';

export const VisionView: React.FC = () => {
  const [cameraLoading, setCameraLoading] = useState(false);
  const [screenLoading, setScreenLoading] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [cameraResult, setCameraResult] = useState<any>(null);
  const [screenResult, setScreenResult] = useState<any>(null);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'airtouch' | 'capture'>('airtouch');

  // Browser Camera Permission & Stream State
  const [permissionStatus, setPermissionStatus] = useState<'prompt' | 'granted' | 'denied'>('prompt');
  const [isStreaming, setIsStreaming] = useState(false);
  const [videoDevices, setVideoDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('');
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);

  // Check initial permissions and enumerate devices
  useEffect(() => {
    checkPermissions();
    enumerateCameras();

    return () => {
      stopCameraStream();
    };
  }, []);

  const checkPermissions = async () => {
    try {
      if (navigator.permissions && navigator.permissions.query) {
        const res = await navigator.permissions.query({ name: 'camera' as any });
        setPermissionStatus(res.state as any);
        res.onchange = () => {
          setPermissionStatus(res.state as any);
          if (res.state === 'granted') {
            enumerateCameras();
          }
        };
      }
    } catch {
      // Permission query unsupported in some webviews
    }
  };

  const enumerateCameras = async () => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoInputs = devices.filter((d) => d.kind === 'videoinput');
      setVideoDevices(videoInputs);
      if (videoInputs.length > 0 && !selectedDeviceId) {
        setSelectedDeviceId(videoInputs[0].deviceId);
      }
    } catch (e) {
      console.warn('Failed to enumerate video devices:', e);
    }
  };

  const requestCameraPermission = async () => {
    setErrorMsg(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: selectedDeviceId ? { deviceId: { exact: selectedDeviceId } } : true,
      });
      setPermissionStatus('granted');
      mediaStreamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
      setIsStreaming(true);
      await enumerateCameras();
    } catch (err: any) {
      setPermissionStatus('denied');
      setErrorMsg(`Camera permission denied or hardware unavailable: ${err.message}`);
      setIsStreaming(false);
    }
  };

  const stopCameraStream = () => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsStreaming(false);
  };

  const handleCaptureFromLiveStream = async () => {
    if (!videoRef.current || !isStreaming) {
      return handleCaptureCameraBackend();
    }

    setCameraLoading(true);
    setErrorMsg(null);

    try {
      const video = videoRef.current;
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      const ctx = canvas.getContext('2d');
      if (!ctx) throw new Error('Could not get canvas context');

      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      // Convert canvas frame to Blob and upload for OCR & Scene Analysis
      canvas.toBlob(async (blob) => {
        if (!blob) {
          throw new Error('Canvas frame conversion failed');
        }
        const formData = new FormData();
        formData.append('file', blob, `frame_${Date.now()}.jpg`);

        const res = await fetch('/api/v1/vision/upload', {
          method: 'POST',
          body: formData,
        });
        const data = await res.json();
        if (res.ok) {
          setCameraResult({
            image_url: data.image_url,
            width: canvas.width,
            height: canvas.height,
            latency_ms: data.latency_ms,
            ocr: data.ocr,
            analysis: data.analysis,
          });
        } else {
          setErrorMsg(data.detail || 'Analysis of live stream frame failed.');
        }
        setCameraLoading(false);
      }, 'image/jpeg', 0.92);
    } catch (err: any) {
      setErrorMsg(`Capture failed: ${err.message}`);
      setCameraLoading(false);
    }
  };

  const handleCaptureCameraBackend = async () => {
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
      {/* Header */}
      <div className="flex items-center justify-between border-b border-matrix-border/50 pb-4">
        <div>
          <h1 className="text-sm font-mono uppercase font-bold text-slate-100 flex items-center gap-2">
            <Eye className="w-4 h-4 text-matrix-cyan" />
            VISION & SCENE INTELLIGENCE (AIRTOUCH + NATIVE OCR + SENSORS)
          </h1>
          <p className="text-xs font-mono text-matrix-textMuted mt-0.5">
            AirTouch Gesture3D & Touchless Scroll · GesturEye Tracking · Physical Webcam · Windows 11 OCR
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

      {/* Permission Status Notification Bar */}
      <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs font-mono">
        <div className="flex items-center gap-3">
          <span className="text-slate-400">CAMERA PERMISSION:</span>
          {permissionStatus === 'granted' ? (
            <span className="px-2 py-0.5 rounded bg-matrix-green/10 border border-matrix-green/40 text-matrix-green flex items-center gap-1.5 font-bold">
              <CheckCircle2 className="w-3.5 h-3.5" /> GRANTED
            </span>
          ) : permissionStatus === 'denied' ? (
            <span className="px-2 py-0.5 rounded bg-matrix-red/10 border border-matrix-red/40 text-matrix-red flex items-center gap-1.5 font-bold">
              <ShieldAlert className="w-3.5 h-3.5" /> DENIED (Enable in Browser Settings)
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/40 text-amber-400 flex items-center gap-1.5 font-bold">
              <AlertCircle className="w-3.5 h-3.5" /> PROMPT / NOT REQUESTED
            </span>
          )}

          {/* Device Selection Dropdown */}
          {videoDevices.length > 0 && (
            <div className="flex items-center gap-2 ml-4">
              <span className="text-slate-400">DEVICE:</span>
              <select
                value={selectedDeviceId}
                onChange={(e) => {
                  setSelectedDeviceId(e.target.value);
                  if (isStreaming) {
                    stopCameraStream();
                  }
                }}
                className="bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-200 text-[11px]"
              >
                {videoDevices.map((d, idx) => (
                  <option key={d.deviceId || idx} value={d.deviceId}>
                    {d.label || `Camera ${idx + 1}`}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Live Stream Request / Stop Button */}
        <div>
          {isStreaming ? (
            <button
              onClick={stopCameraStream}
              className="px-3 py-1 rounded-lg bg-matrix-red/20 border border-matrix-red text-matrix-red text-xs font-mono font-bold flex items-center gap-1.5 hover:bg-matrix-red/30 transition-all"
            >
              <VideoOff className="w-3.5 h-3.5" />
              <span>STOP STREAM</span>
            </button>
          ) : (
            <button
              onClick={requestCameraPermission}
              className="px-3 py-1 rounded-lg bg-matrix-cyan text-slate-950 text-xs font-mono font-bold flex items-center gap-1.5 hover:bg-cyan-300 transition-all shadow-md shadow-matrix-cyan/20"
            >
              <Video className="w-3.5 h-3.5" />
              <span>{permissionStatus === 'granted' ? 'START LIVE PREVIEW' : 'GRANT CAMERA ACCESS'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-matrix-border/40 pb-2">
        <button
          onClick={() => setActiveTab('airtouch')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-mono font-bold transition-all ${
            activeTab === 'airtouch'
              ? 'bg-matrix-cyan text-slate-950 shadow-md shadow-matrix-cyan/20'
              : 'text-slate-400 hover:text-slate-200 bg-slate-900/60 border border-slate-800'
          }`}
        >
          <Hand className="w-3.5 h-3.5" />
          <span>AIRTOUCH VISION & GESTURE STUDIO</span>
        </button>
        <button
          onClick={() => setActiveTab('capture')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-mono font-bold transition-all ${
            activeTab === 'capture'
              ? 'bg-matrix-cyan text-slate-950 shadow-md shadow-matrix-cyan/20'
              : 'text-slate-400 hover:text-slate-200 bg-slate-900/60 border border-slate-800'
          }`}
        >
          <Camera className="w-3.5 h-3.5" />
          <span>HARDWARE CAMERA & DESKTOP OCR</span>
        </button>
      </div>

      {activeTab === 'airtouch' ? (
        <AirTouchStudio />
      ) : (
        <>
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
                  onClick={isStreaming ? handleCaptureFromLiveStream : handleCaptureCameraBackend}
                  disabled={cameraLoading}
                  className="px-3 py-1.5 rounded-lg bg-matrix-cyan text-slate-950 font-mono font-bold text-xs hover:bg-cyan-300 disabled:opacity-40 transition-colors flex items-center gap-1.5"
                >
                  <Camera className="w-3.5 h-3.5" />
                  <span>{cameraLoading ? 'ANALYZING...' : isStreaming ? 'SNAPSHOT STREAM' : 'CAPTURE FRAME'}</span>
                </button>
              </div>

              <div className="min-h-56 rounded-lg bg-slate-950/80 border border-matrix-border/60 flex items-center justify-center overflow-hidden relative">
                {/* Real Live Browser Video Preview Element */}
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className={`w-full max-h-56 object-cover rounded ${isStreaming ? 'block' : 'hidden'}`}
                />

                {!isStreaming && cameraResult && cameraResult.image_url ? (
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
                    {cameraResult.ocr?.text && (
                      <div className="p-2 rounded bg-slate-900 border border-slate-800 text-[10px] text-matrix-cyan max-h-20 overflow-y-auto">
                        OCR: {cameraResult.ocr.text}
                      </div>
                    )}
                  </div>
                ) : !isStreaming ? (
                  <div className="text-center font-mono text-xs text-slate-500 space-y-2 p-6">
                    <Camera className="w-8 h-8 mx-auto opacity-40 mb-1" />
                    <div>Webcam Standby</div>
                    <button
                      onClick={requestCameraPermission}
                      className="px-3 py-1 text-[11px] rounded bg-slate-900 hover:bg-slate-800 text-matrix-cyan border border-matrix-cyan/30"
                    >
                      Click to activate live webcam stream
                    </button>
                  </div>
                ) : null}
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

              <div className="min-h-56 rounded-lg bg-slate-950/80 border border-matrix-border/60 flex items-center justify-center overflow-hidden relative">
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
                    <Monitor className="w-8 h-8 mx-auto opacity-40 mb-1" />
                    <span>Desktop Stream Standby</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
