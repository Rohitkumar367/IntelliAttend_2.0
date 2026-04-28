import { useEffect, useRef, useState } from "react";
import { FaceDetector, FilesetResolver } from "@mediapipe/tasks-vision";

const VISION_WASM_URL = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm";
const FACE_MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite";

function clamp01(value) {
  return Math.max(0, Math.min(1, Number(value) || 0));
}

export function useFaceDetectionOverlay({
  videoRef,
  enabled,
  minDetectionConfidence = 0.45,
  frameSkip = 1,
}) {
  const [faces, setFaces] = useState([]);
  const [detectorReady, setDetectorReady] = useState(false);

  const detectorRef = useRef(null);
  const rafRef = useRef(null);
  const disposedRef = useRef(false);
  const processingRef = useRef(false);
  const frameCounterRef = useRef(0);

  useEffect(() => {
    disposedRef.current = false;

    if (!enabled) {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      setFaces([]);
      setDetectorReady(false);
      return () => {
        disposedRef.current = true;
      };
    }

    const initialize = async () => {
      try {
        const vision = await FilesetResolver.forVisionTasks(VISION_WASM_URL);

        if (disposedRef.current) {
          return;
        }

        detectorRef.current = await FaceDetector.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath: FACE_MODEL_URL,
          },
          runningMode: "VIDEO",
          minDetectionConfidence,
        });

        if (disposedRef.current) {
          return;
        }

        setDetectorReady(true);

        const detectLoop = () => {
          if (disposedRef.current) {
            return;
          }

          rafRef.current = requestAnimationFrame(detectLoop);

          const detector = detectorRef.current;
          const video = videoRef?.current;
          if (!detector || !video) {
            return;
          }

          if (video.readyState < 2 || video.videoWidth <= 0 || video.videoHeight <= 0) {
            return;
          }

          if (processingRef.current) {
            return;
          }

          frameCounterRef.current += 1;
          if (frameSkip > 1 && frameCounterRef.current % frameSkip !== 0) {
            return;
          }

          processingRef.current = true;

          try {
            const result = detector.detectForVideo(video, performance.now());
            const detections = Array.isArray(result?.detections) ? result.detections : [];
            const vw = video.videoWidth || 1;
            const vh = video.videoHeight || 1;

            const nextFaces = detections
              .map((detection, idx) => {
                const box = detection.boundingBox;
                if (!box) return null;

                const x = clamp01((box.originX || 0) / vw);
                const y = clamp01((box.originY || 0) / vh);
                const width = clamp01((box.width || 0) / vw);
                const height = clamp01((box.height || 0) / vh);
                const score = Number(detection.categories?.[0]?.score || 0);

                if (width <= 0 || height <= 0) {
                  return null;
                }

                return {
                  id: `${idx}-${x.toFixed(4)}-${y.toFixed(4)}`,
                  bbox_xmin: x,
                  bbox_ymin: y,
                  bbox_width: width,
                  bbox_height: height,
                  detection_confidence: clamp01(score),
                };
              })
              .filter(Boolean);

            setFaces(nextFaces);
          } catch {
            // Ignore frame-level detection errors and continue loop.
          } finally {
            processingRef.current = false;
          }
        };

        detectLoop();
      } catch {
        setDetectorReady(false);
      }
    };

    initialize();

    return () => {
      disposedRef.current = true;
      processingRef.current = false;
      frameCounterRef.current = 0;

      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }

      if (detectorRef.current && typeof detectorRef.current.close === "function") {
        detectorRef.current.close();
      }
      detectorRef.current = null;

      setDetectorReady(false);
      setFaces([]);
    };
  }, [enabled, frameSkip, minDetectionConfidence, videoRef]);

  return {
    faces,
    detectorReady,
  };
}
