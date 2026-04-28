import logging
import threading
import time
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

from app.db import repository
from app.core.config import settings
from app.services.embedding_service import rebuild_embeddings, ensure_embeddings_loaded
from app.services.remote_training_service import get_hf_training_status, launch_hf_training_job
from app.services.training_service import (
    complete_training,
    fail_training,
    set_training_remote_job,
    update_training_stage,
)


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _training_manifest() -> list[dict[str, str]]:
    rows = repository.list_all_images()
    manifest: list[dict[str, str]] = []

    for row in rows:
        url = row.get("url")
        if not url:
            continue

        manifest.append(
            {
                "student_id": str(row.get("student_id", "")),
                "student_name": str(row.get("student_name", "")),
                "image_url": str(url),
            }
        )

    return manifest


def run_training_pipeline_async(run_id: str, epochs: int, batch_size: int) -> None:
    def _runner() -> None:
        try:
            update_training_stage(
                run_id,
                "collecting",
                "Collecting training image manifest",
                progress_percent=5.0,
                remote_status="collecting",
            )

            manifest = _training_manifest()
            if not manifest:
                fail_training(run_id=run_id, error_message="No student images available for training")
                return

            update_training_stage(
                run_id,
                "submitting",
                f"Submitting VGGFace training job with {len(manifest)} images",
                progress_percent=12.0,
                remote_status="submitting",
            )

            launch_data = launch_hf_training_job(
                run_id=run_id,
                epochs=epochs,
                batch_size=batch_size,
                images_manifest=manifest,
            )
            remote_job_id = str(launch_data.get("job_id", "")).strip()
            if not remote_job_id:
                fail_training(run_id=run_id, error_message="Remote trainer did not provide job id")
                return

            set_training_remote_job(run_id=run_id, remote_job_id=remote_job_id)

            update_training_stage(
                run_id,
                "remote_queued",
                launch_data.get("message") or "Remote training job queued",
                progress_percent=_to_float(launch_data.get("progress")) or 15.0,
                remote_status=str(launch_data.get("status", "queued")),
            )

            start = time.monotonic()
            timeout = settings.hf_training_timeout_seconds

            while True:
                elapsed = time.monotonic() - start
                if elapsed > timeout:
                    fail_training(
                        run_id=run_id,
                        error_message="Remote training timed out",
                        error_detail=f"No terminal status within {timeout} seconds",
                    )
                    return

                time.sleep(settings.hf_poll_interval_seconds)
                status_data = get_hf_training_status(remote_job_id)

                remote_status = str(status_data.get("status", "running")).lower()
                stage = str(status_data.get("stage") or remote_status)
                message = str(status_data.get("message") or f"Remote training status: {remote_status}")
                progress = _to_float(status_data.get("progress"))
                artifact_url = status_data.get("artifact_url")
                artifact_revision = status_data.get("artifact_revision")
                metrics = status_data.get("metrics") if isinstance(status_data.get("metrics"), dict) else None

                if remote_status in {"queued", "starting", "running", "processing", "uploading"}:
                    update_training_stage(
                        run_id,
                        stage,
                        message,
                        progress_percent=progress,
                        remote_status=remote_status,
                    )
                    continue

                if remote_status in {"completed", "succeeded", "success"}:
                    update_training_stage(
                        run_id,
                        "finalizing",
                        "Refreshing embeddings for attendance pipeline",
                        progress_percent=95.0,
                        remote_status="finalizing",
                    )

                    rebuild_embeddings()
                    ensure_embeddings_loaded()

                    remote_message = str(message or "").strip()
                    lower_message = remote_message.lower()
                    completion_message = "Training completed successfully."

                    if (
                        "without artifact upload" in lower_message
                        or "rate limit" in lower_message
                        or "warning" in lower_message
                    ):
                        completion_message = remote_message
                    elif not artifact_url:
                        completion_message = "Training completed with warning: artifact upload unavailable."

                    version = str(artifact_revision or datetime.utcnow().strftime("vggface_%Y%m%d_%H%M%S"))
                    complete_training(
                        run_id=run_id,
                        model_version=version,
                        artifact_url=str(artifact_url) if artifact_url else None,
                        artifact_revision=str(artifact_revision) if artifact_revision else None,
                        metrics=metrics,
                        completion_message=completion_message,
                    )
                    return

                if remote_status in {"failed", "error", "cancelled", "canceled"}:
                    fail_training(
                        run_id=run_id,
                        error_message=message,
                        error_detail=str(status_data.get("error") or message),
                    )
                    return

                update_training_stage(
                    run_id,
                    stage,
                    message,
                    progress_percent=progress,
                    remote_status=remote_status,
                )

        except Exception as exc:
            logger.error(f"Training failed: {exc}")
            fail_training(run_id=run_id, error_message="Remote training orchestration failed", error_detail=str(exc))

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
