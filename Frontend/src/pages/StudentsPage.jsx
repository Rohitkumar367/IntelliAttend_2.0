import { useEffect, useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";
import StudentTable from "../components/StudentTable";
import ConfirmDeleteDialog from "../components/ConfirmDeleteDialog";
import FaceOverlayCanvas from "../components/FaceOverlayCanvas";
import { useFaceDetectionOverlay } from "../hooks/useFaceDetectionOverlay";
import { useAppStore } from "../store/useAppStore";

const CAPTURE_COUNT = 50;
const FACE_CROP_SIZE = 224;

function wait(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function pickSingleFace(faces) {
  if (!Array.isArray(faces) || faces.length === 0) {
    throw new Error("No face detected. Keep one face clearly in view.");
  }

  if (faces.length > 1) {
    throw new Error("Multiple faces detected. Keep only one face in view while adding student.");
  }

  return faces[0];
}

export default function StudentsPage({ students }) {
  const addStudent = useAppStore((state) => state.addStudent);
  const deleteStudent = useAppStore((state) => state.deleteStudent);
  const [name, setName] = useState("");
  const [rollNo, setRollNo] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const [captureProgress, setCaptureProgress] = useState(0);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  const { faces: liveFaces, detectorReady } = useFaceDetectionOverlay({
    videoRef,
    enabled: cameraReady,
    frameSkip: 2,
    minDetectionConfidence: 0.45,
  });

  const capturePercent = useMemo(
    () => Math.round((captureProgress / CAPTURE_COUNT) * 100),
    [captureProgress]
  );

  const liveFaceBoxes = useMemo(
    () =>
      (liveFaces || []).map((face) => ({
        ...face,
        color: "#22c55e",
      })),
    [liveFaces]
  );

  const enrollmentFaceState = useMemo(() => {
    if (!cameraReady) {
      return {
        label: "Camera off",
        detail: "Start camera to validate face count.",
        badgeClass: "bg-slate-100 text-slate-700 border-slate-200",
      };
    }

    if (!detectorReady) {
      return {
        label: "Detector loading",
        detail: "Please wait for face detector to be ready.",
        badgeClass: "bg-amber-100 text-amber-700 border-amber-200",
      };
    }

    if (liveFaces.length === 1) {
      return {
        label: "Ready: 1 face",
        detail: "Great. Exactly one face is visible for enrollment.",
        badgeClass: "bg-emerald-100 text-emerald-700 border-emerald-200",
      };
    }

    if (liveFaces.length === 0) {
      return {
        label: "No face",
        detail: "Place one face clearly in front of the camera.",
        badgeClass: "bg-rose-100 text-rose-700 border-rose-200",
      };
    }

    return {
      label: `Blocked: ${liveFaces.length} faces`,
      detail: "Keep only one face in frame while adding a student.",
      badgeClass: "bg-rose-100 text-rose-700 border-rose-200",
    };
  }, [cameraReady, detectorReady, liveFaces.length]);

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  async function startCamera() {
    if (streamRef.current) return;
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    streamRef.current = stream;
    if (videoRef.current) {
      videoRef.current.srcObject = stream;
      await videoRef.current.play();
    }
    setCameraReady(true);
  }

  async function handleStartCamera() {
    try {
      await startCamera();
      setStatus("Camera started.");
      toast.success("Camera started.");
    } catch (error) {
      setStatus(`Camera error: ${error.message}`);
      toast.error(`Camera error: ${error.message}`);
    }
  }

  function handleStopCamera() {
    stopCamera();
    setStatus("Camera stopped.");
  }

  function stopCamera() {
    if (!streamRef.current) return;
    streamRef.current.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setCameraReady(false);
  }

  async function captureFrame(index) {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) {
      throw new Error("Camera is not ready");
    }
    const width = video.videoWidth || 640;
    const height = video.videoHeight || 480;
    const ctx = canvas.getContext("2d");
    const primaryFace = pickSingleFace(liveFaces);

    const faceX = Number(primaryFace.bbox_xmin || 0) * width;
    const faceY = Number(primaryFace.bbox_ymin || 0) * height;
    const faceW = Number(primaryFace.bbox_width || 0) * width;
    const faceH = Number(primaryFace.bbox_height || 0) * height;

    if (faceW < 8 || faceH < 8) {
      throw new Error("Detected face is too small. Move closer to the camera.");
    }

    const centerX = faceX + faceW / 2;
    const centerY = faceY + faceH / 2;
    const side = Math.max(faceW, faceH) * 1.35;
    const cropSize = Math.max(16, Math.min(side, width, height));
    const cropX = clamp(centerX - cropSize / 2, 0, width - cropSize);
    const cropY = clamp(centerY - cropSize / 2, 0, height - cropSize);

    canvas.width = FACE_CROP_SIZE;
    canvas.height = FACE_CROP_SIZE;
    ctx.drawImage(
      video,
      cropX,
      cropY,
      cropSize,
      cropSize,
      0,
      0,
      FACE_CROP_SIZE,
      FACE_CROP_SIZE
    );

    const blob = await new Promise((resolve, reject) => {
      canvas.toBlob(
        (generatedBlob) => {
          if (!generatedBlob) {
            reject(new Error("Failed to capture frame"));
            return;
          }
          resolve(generatedBlob);
        },
        "image/jpeg",
        0.92
      );
    });

    return new File([blob], `capture_${String(index + 1).padStart(2, "0")}.jpg`, {
      type: "image/jpeg",
    });
  }

  async function captureFiftyImages() {
    const snapshots = [];
    let attempts = 0;
    let lastCaptureIssue = "";

    while (snapshots.length < CAPTURE_COUNT) {
      attempts += 1;
      if (attempts > CAPTURE_COUNT * 10) {
        throw new Error(lastCaptureIssue || "Could not capture enough face crops. Keep one face steady and try again.");
      }

      try {
        const frame = await captureFrame(snapshots.length);
        snapshots.push(frame);
        setCaptureProgress(snapshots.length);
        lastCaptureIssue = "";
      } catch (error) {
        lastCaptureIssue = error?.message || "Face crop capture failed.";
        // Skip frames without a usable face crop and keep trying.
      }

      await wait(90);
    }

    return snapshots;
  }

  async function handleAddFromCamera() {
    if (!name.trim()) {
      setStatus("Please enter student name first.");
      toast.error("Please enter student name first.");
      return;
    }
    setBusy(true);
    setCaptureProgress(0);
    setStatus("Capturing 50 face crops from camera...");
    try {
      if (!cameraReady) {
        await startCamera();
        await wait(250);
      }

      const images = await captureFiftyImages();
      setStatus("Uploading selected images to backend/Cloudinary...");

      const created = await addStudent({ name, roll_no: rollNo || null, images });
      setName("");
      setRollNo("");
      setCaptureProgress(0);
      setStatus(
        `Added successfully. Captured ${created.captured_images || CAPTURE_COUNT}, stored ${created.stored_images || 0} images.`
      );
      toast.success("Student added successfully.");
    } catch (error) {
      setStatus(`Failed: ${error.message}`);
      toast.error(`Add student failed: ${error.message}`);
    } finally {
      setBusy(false);
    }
  }

  async function confirmDelete() {
    if (!selectedStudent) return;
    setBusy(true);
    setStatus("Deleting student...");
    try {
      await deleteStudent(selectedStudent.id);
      setSelectedStudent(null);
      setStatus("Student deleted.");
      toast.success("Student deleted.");
    } catch (error) {
      setStatus(`Failed: ${error.message}`);
      toast.error(`Delete failed: ${error.message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-[1.15fr_1fr]">
        <div className="rounded-2xl bg-white p-5 shadow-xl shadow-slate-200/70">
          <h3 className="text-lg font-semibold text-slate-900">Add Student (Auto capture 50)</h3>
          <p className="mt-1 text-sm text-slate-600">
            Fill details, open camera, then capture and upload 50 cropped face images.
          </p>

          <div className="mt-4 grid gap-3">
            <input
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none ring-blue-500 focus:ring"
              placeholder="Student name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={busy}
            />
            <input
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none ring-blue-500 focus:ring"
              placeholder="Roll number (optional)"
              value={rollNo}
              onChange={(e) => setRollNo(e.target.value)}
              disabled={busy}
            />
          </div>

          <div className="mt-4 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={handleStartCamera}
              disabled={busy || cameraReady}
              className="rounded-lg bg-slate-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              Start Camera
            </button>
            <button
              type="button"
              onClick={handleStopCamera}
              disabled={busy || !cameraReady}
              className="rounded-lg bg-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 disabled:opacity-50"
            >
              Stop Camera
            </button>
            <button
              type="button"
              onClick={handleAddFromCamera}
              disabled={busy || !name.trim()}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              {busy ? "Processing..." : "Capture 50 & Add Student"}
            </button>
          </div>

          <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full bg-blue-600 transition-all"
              style={{ width: `${capturePercent}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Capture progress: {captureProgress}/{CAPTURE_COUNT}
          </p>
          {status ? <p className="mt-3 text-sm text-slate-700">{status}</p> : null}
        </div>

        <div className="rounded-2xl bg-white p-5 shadow-xl shadow-slate-200/70">
          <h4 className="text-sm font-semibold text-slate-900">Live Camera</h4>
          <div className="relative mt-3 overflow-hidden rounded-xl border border-slate-200 bg-slate-950">
            <video ref={videoRef} className="aspect-video w-full object-contain" muted playsInline />
            <FaceOverlayCanvas videoRef={videoRef} boxes={liveFaceBoxes} enabled={cameraReady} />
            <canvas ref={canvasRef} className="hidden" />
          </div>
          <p className="mt-2 text-xs text-slate-500">
            {cameraReady
              ? `Camera ready. Live faces: ${liveFaces.length}. Detector: ${detectorReady ? "ready" : "loading"}.`
              : "Camera is off."}
          </p>
          <div className="mt-2 flex items-start gap-2">
            <span
              className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${enrollmentFaceState.badgeClass}`}
            >
              {enrollmentFaceState.label}
            </span>
            <p className="text-xs text-slate-600">{enrollmentFaceState.detail}</p>
          </div>
          <p className="mt-1 text-xs text-amber-600">
            For student registration, keep exactly one face in frame.
          </p>
        </div>
      </div>

      <div className="rounded-2xl bg-white p-5 shadow-xl shadow-slate-200/70">
        <h3 className="text-lg font-semibold text-slate-900">Students</h3>
        <StudentTable students={students} onDelete={setSelectedStudent} />
      </div>

      <ConfirmDeleteDialog
        open={Boolean(selectedStudent)}
        title="Delete Student"
        message={selectedStudent ? `Delete ${selectedStudent.name} and all linked data?` : ""}
        onConfirm={confirmDelete}
        onCancel={() => setSelectedStudent(null)}
      />
    </section>
  );
}
