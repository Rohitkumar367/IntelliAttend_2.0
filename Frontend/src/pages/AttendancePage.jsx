import { useEffect, useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";
import FaceOverlayCanvas from "../components/FaceOverlayCanvas";
import { useFaceDetectionOverlay } from "../hooks/useFaceDetectionOverlay";
import { useAppStore } from "../store/useAppStore";

function dataUrlToFile(dataUrl, filename) {
  const [meta, base64] = dataUrl.split(",");
  const mime = meta.match(/:(.*?);/)[1];
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return new File([bytes], filename, { type: mime });
}

export default function AttendancePage() {
  const recognizeAttendanceFrame = useAppStore((state) => state.recognizeAttendanceFrame);
  const getAttendanceLockState = useAppStore((state) => state.getAttendanceLockState);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const timerRef = useRef(null);
  const requestInFlightRef = useRef(false);
  const lastErrorToastAtRef = useRef(0);
  const lockToastAtRef = useRef(0);

  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState("Idle");
  const [lastResult, setLastResult] = useState(null);
  const [scanCount, setScanCount] = useState(0);

  const { faces: liveFaces, detectorReady } = useFaceDetectionOverlay({
    videoRef,
    enabled: running,
    frameSkip: 1,
    minDetectionConfidence: 0.45,
  });

  const isStatusAlert = String(status || "").toLowerCase() !== "running";
  const recognitionResults = Array.isArray(lastResult?.results) ? lastResult.results : [];

  const overlayBoxes = useMemo(
    () =>
      (liveFaces || []).map((face, idx) => {
        const recognized = recognitionResults[idx];
        if (!recognized) {
          return {
            ...face,
            color: "#ef4444",
            label: "Unknown",
          };
        }

        const isKnown = Boolean(recognized.student_id);
        const name = recognized.name || "Unknown";
        const confidence = Number(recognized.confidence || 0);

        return {
          ...face,
          color: isKnown ? "#22c55e" : "#ef4444",
          label: `${name} ${(confidence * 100).toFixed(0)}%`,
        };
      }),
    [liveFaces, recognitionResults]
  );

  useEffect(() => {
    return () => {
      stopLoop();
      stopCamera();
    };
  }, []);

  async function startCamera() {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    if (videoRef.current) {
      videoRef.current.srcObject = stream;
      await videoRef.current.play();
    }
  }

  function stopCamera() {
    const stream = videoRef.current?.srcObject;
    if (!stream) return;
    stream.getTracks().forEach((track) => track.stop());
    if (videoRef.current) videoRef.current.srcObject = null;
  }

  function stopLoop() {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setRunning(false);
  }

  async function captureAndRecognize() {
    if (!videoRef.current || !canvasRef.current) return;
    if (requestInFlightRef.current) return;

    requestInFlightRef.current = true;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
    const file = dataUrlToFile(dataUrl, "frame.jpg");

    try {
      const result = await recognizeAttendanceFrame(file);
      setLastResult(result);
      setScanCount((prev) => prev + 1);

      const attendanceEnabled = result?.attendance_enabled !== false;
      if (!attendanceEnabled) {
        const lockMessage = result?.message || "Attendance is locked. Retrain model to continue.";
        setStatus(lockMessage);

        const now = Date.now();
        if (now - lockToastAtRef.current > 8000) {
          toast(lockMessage);
          lockToastAtRef.current = now;
        }
      } else {
        setStatus("Running");
      }
    } catch (error) {
      setStatus(`Recognition failed: ${error.message}`);
      const now = Date.now();
      if (now - lastErrorToastAtRef.current > 6000) {
        toast.error(`Recognition failed: ${error.message}`);
        lastErrorToastAtRef.current = now;
      }
    } finally {
      requestInFlightRef.current = false;
    }
  }

  async function start() {
    try {
      const lockState = await getAttendanceLockState();
      const attendanceEnabled = lockState?.attendance_enabled !== false;

      if (!attendanceEnabled) {
        const lockMessage =
          lockState?.message ||
          "Train model first because student data changed (added/deleted).";
        setStatus(lockMessage);
        toast.error(lockMessage);
        return;
      }

      await startCamera();
      setStatus("Camera started");
      toast.success("Camera started.");
      setRunning(true);
      timerRef.current = setInterval(() => {
        captureAndRecognize();
      }, 2000);
    } catch (error) {
      setStatus(`Camera error: ${error.message}`);
      toast.error(`Camera error: ${error.message}`);
    }
  }

  function stop() {
    stopLoop();
    stopCamera();
    setStatus("Stopped");
    toast("Attendance stopped.");
  }

  return (
    <section className="space-y-6">
      <div className="rounded-2xl bg-white p-5 shadow-xl shadow-slate-200/70">
        <h3 className="text-lg font-semibold text-slate-900">Mark Attendance (Multi-face)</h3>
        <p className="mt-1 text-sm text-slate-600">
          Start camera on the left. Marked recognition records appear on the right.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <div className="rounded-2xl bg-white p-6 shadow-xl shadow-slate-200/70">
          <div className="flex flex-wrap gap-3">
            <button
              onClick={start}
              disabled={running}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              Start Attendance
            </button>
            <button
              className="rounded-lg bg-slate-200 px-4 py-2 text-sm font-semibold text-slate-700"
              onClick={stop}
              disabled={!running}
            >
              Stop
            </button>
          </div>

          <div className="relative mt-5 overflow-hidden rounded-xl border border-slate-200 bg-slate-950">
            <video ref={videoRef} className="aspect-video w-full object-contain" muted playsInline />
            <FaceOverlayCanvas videoRef={videoRef} boxes={overlayBoxes} enabled={running} />
            <canvas ref={canvasRef} style={{ display: "none" }} />
          </div>

          <p className="mt-2 text-xs text-slate-500">
            {running
              ? `Live faces: ${liveFaces.length}. Detector: ${detectorReady ? "ready" : "loading"}.`
              : "Start attendance to enable live face tracking."}
          </p>
        </div>

        <div className="rounded-2xl bg-white p-6 shadow-xl shadow-slate-200/70">
        <h4 className="text-base font-semibold text-slate-900">Last Recognition Results</h4>
        {!lastResult ? (
          <p className="mt-2 text-sm text-slate-600">No frame processed yet.</p>
        ) : (
          <div className="mt-3 space-y-3">
            <p className="text-sm text-slate-700">
              Recognized {lastResult?.recognized_faces ?? 0} of {lastResult?.total_faces ?? 0} faces.
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              {(lastResult.results || []).map((result, idx) => {
                const markedItem = (lastResult.marked || []).find(
                  (item) => String(item.student_id) === String(result.student_id)
                );
                return (
                  <div key={`${result.student_id || "unknown"}-${idx}`} className="rounded-lg border border-slate-200 p-3">
                    <p className="font-semibold text-slate-900">{result.name || "Unknown"}</p>
                    <p className="text-xs text-slate-500">
                      Confidence: {Number(result.confidence || 0).toFixed(2)}
                    </p>
                    <p className="mt-1 text-xs">
                      {markedItem?.attendance_marked ? (
                        <span className="font-semibold text-emerald-600">Attendance Marked</span>
                      ) : (
                        <span className="font-semibold text-amber-600">
                          Not marked (already marked today or not a class day)
                        </span>
                      )}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div
            className={`rounded-xl border p-3 ${
              isStatusAlert ? "border-red-300" : "border-slate-200"
            }`}
          >
            <p className="text-xs text-slate-500">Status</p>
            <p className="text-sm font-semibold text-red-600">{status}</p>
          </div>
          <div className="rounded-xl border border-slate-200 p-3">
            <p className="text-xs text-slate-500">Scans</p>
            <p className="text-sm font-semibold text-slate-900">{scanCount}</p>
          </div>
          <div className="rounded-xl border border-slate-200 p-3">
            <p className="text-xs text-slate-500">Faces (last frame)</p>
            <p className="text-sm font-semibold text-slate-900">
              {Math.max(lastResult?.total_faces ?? 0, liveFaces.length)}
            </p>
          </div>
        </div>
        </div>
      </div>
    </section>
  );
}
