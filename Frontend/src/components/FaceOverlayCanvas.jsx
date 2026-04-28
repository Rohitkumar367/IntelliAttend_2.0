import { useEffect, useRef } from "react";

function clamp01(value) {
  return Math.max(0, Math.min(1, Number(value) || 0));
}

export default function FaceOverlayCanvas({ videoRef, boxes, enabled }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const video = videoRef?.current;
    if (!canvas || !video) return;

    const updateCanvasSize = () => {
      const width = Math.max(1, Math.floor(video.clientWidth || 0));
      const height = Math.max(1, Math.floor(video.clientHeight || 0));
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }
    };

    updateCanvasSize();

    const observer = new ResizeObserver(() => {
      updateCanvasSize();
      draw();
    });

    observer.observe(video);

    const ctx = canvas.getContext("2d");

    const draw = () => {
      updateCanvasSize();

      if (!ctx) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (!enabled) return;

      for (const box of boxes || []) {
        const x = clamp01(box.bbox_xmin) * canvas.width;
        const y = clamp01(box.bbox_ymin) * canvas.height;
        const w = clamp01(box.bbox_width) * canvas.width;
        const h = clamp01(box.bbox_height) * canvas.height;

        if (w <= 1 || h <= 1) continue;

        const color = box.color || "#22c55e";
        const label = box.label || "";

        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, w, h);

        if (label) {
          ctx.font = "12px sans-serif";
          const textWidth = ctx.measureText(label).width;
          const labelPaddingX = 6;
          const labelHeight = 18;
          const labelX = x;
          const labelY = Math.max(0, y - labelHeight - 2);
          const labelWidth = textWidth + labelPaddingX * 2;

          ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
          ctx.fillRect(labelX, labelY, labelWidth, labelHeight);

          ctx.fillStyle = color;
          ctx.fillText(label, labelX + labelPaddingX, labelY + 13);
        }
      }
    };

    draw();

    return () => {
      observer.disconnect();
      if (ctx) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
    };
  }, [boxes, enabled, videoRef]);

  return <canvas ref={canvasRef} className="pointer-events-none absolute inset-0 z-10" />;
}
