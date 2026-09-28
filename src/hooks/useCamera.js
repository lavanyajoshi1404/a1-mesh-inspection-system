import { useState, useRef, useEffect } from 'react';

export function useCamera({ selectedProfile, setInspectionResult, setInspectionError, fetchStats }) {
  const [cameraActive,  setCameraActive]  = useState(false);
  const [cameraStream,  setCameraStream]  = useState(null);
  const [cameraError,   setCameraError]   = useState('');
  const [autoScan,      setAutoScan]      = useState(false);
  const [inspecting,    setInspecting]    = useState(false);

  const videoRef        = useRef(null);
  const canvasRef       = useRef(null);
  const scanIntervalRef = useRef(null);
  const scanInFlightRef = useRef(false);

  // Attach stream to video element when it becomes available
  useEffect(() => {
    if (cameraActive && cameraStream && videoRef.current) {
      videoRef.current.srcObject = cameraStream;
      videoRef.current.play().catch((err) => {
        setCameraError(`Camera preview error: ${err.message}`);
      });
    }
  }, [cameraActive, cameraStream]);

  // Stop all tracks on stream change / unmount
  useEffect(() => () => cameraStream?.getTracks().forEach(t => t.stop()), [cameraStream]);

  // Auto-scan interval
  useEffect(() => {
    if (cameraActive && autoScan) {
      scanIntervalRef.current = setInterval(() => captureCameraFrame(), 1500);
    } else {
      if (scanIntervalRef.current) { clearInterval(scanIntervalRef.current); scanIntervalRef.current = null; }
    }
    return () => { if (scanIntervalRef.current) clearInterval(scanIntervalRef.current); };
  }, [cameraActive, autoScan]);

  const toggleCamera = async () => {
    if (cameraActive) {
      setAutoScan(false);
      cameraStream?.getTracks().forEach(t => t.stop());
      setCameraStream(null);
      if (videoRef.current) videoRef.current.srcObject = null;
      setCameraActive(false);
      setCameraError('');
    } else {
      if (!navigator.mediaDevices?.getUserMedia) {
        setCameraError('Camera access is not supported by this browser context.');
        return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: { ideal: 'environment' } },
        });
        setCameraStream(stream);
        setCameraActive(true);
        setCameraError('');
        setAutoScan(true);
        setTimeout(() => captureCameraFrame(), 500);
      } catch (e) {
        setCameraError(e.message || 'Could not connect to camera sensor.');
      }
    }
  };

  const captureCameraFrame = async () => {
    if (scanInFlightRef.current) return;
    if (!videoRef.current || !canvasRef.current) return;
    if (videoRef.current.readyState < 2) {
      setTimeout(() => captureCameraFrame(), 250);
      return;
    }
    const video  = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width  = video.videoWidth  || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const b64 = canvas.toDataURL('image/jpeg', 0.85);
    scanInFlightRef.current = true;
    setInspecting(true);
    setCameraError('');
    setInspectionError('');
    try {
      const res  = await fetch('/api/inspect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_b64: b64, filename: 'live_webcam_frame.jpg', profile_id: selectedProfile.id }),
      });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || 'Camera frame analysis failed');
      setInspectionResult(data);
      fetchStats();
    } catch (err) {
      console.error('Camera inspection error:', err);
      setInspectionError(err.message || 'Frame analysis failed.');
      setAutoScan(false);
    } finally {
      scanInFlightRef.current = false;
      setInspecting(false);
    }
  };

  return {
    cameraActive, cameraStream, cameraError,
    autoScan, setAutoScan,
    inspecting,
    videoRef, canvasRef,
    toggleCamera, captureCameraFrame,
  };
}
