from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.db import repository

logger = logging.getLogger(__name__)

_active_run_id: str | None = None


def _parse_started_at(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def _is_stale_queued_run(run: dict) -> bool:
    if run.get("status") != "running":
        return False

    stage = str(run.get("stage") or "").lower()
    remote_job_id = str(run.get("remote_job_id") or "").strip()

    if stage not in {"queued", "collecting", "submitting"}:
        return False

    if remote_job_id:
        return False

    started = _parse_started_at(run.get("started_at"))
    if started is None:
        return False

    stale_after_seconds = max(120, settings.hf_poll_interval_seconds * 10)
    age_seconds = (datetime.now(timezone.utc) - started).total_seconds()
    return age_seconds >= stale_after_seconds


def start_training(epochs: int, batch_size: int) -> dict:
    global _active_run_id

    if _active_run_id:
        latest = repository.latest_training_run()
        if latest and str(latest.get("id")) == _active_run_id and latest.get("status") == "running":
            if _is_stale_queued_run(latest):
                repository.update_training_run(
                    run_id=_active_run_id,
                    status="failed",
                    stage="failed",
                    message="Stale queued run auto-failed",
                    remote_status="failed",
                    error_detail="No remote job assigned for too long",
                )
                logger.warning(f"Auto-failed stale queued run: {_active_run_id}")
                _active_run_id = None
            else:
                return {
                    "status": "running",
                    "stage": latest.get("stage") or "in_progress",
                    "message": "Training already in progress",
                    "run_id": _active_run_id,
                    "already_running": True,
                }
        else:
            _active_run_id = None

    latest = repository.latest_training_run()
    if latest and latest.get("status") == "running" and latest.get("id"):
        if _is_stale_queued_run(latest):
            stale_run_id = str(latest["id"])
            repository.update_training_run(
                run_id=stale_run_id,
                status="failed",
                stage="failed",
                message="Stale queued run auto-failed",
                remote_status="failed",
                error_detail="No remote job assigned for too long",
            )
            logger.warning(f"Auto-failed stale queued run from DB: {stale_run_id}")
            _active_run_id = None
        else:
            _active_run_id = str(latest["id"])
            return {
                "status": "running",
                "stage": latest.get("stage") or "in_progress",
                "message": "Training already in progress",
                "run_id": _active_run_id,
                "already_running": True,
            }

    if repository.count_students() == 0:
        return {
            "status": "failed",
            "stage": "idle",
            "message": "No students available for training",
        }

    dataset_size = repository.count_images()
    if dataset_size == 0:
        return {
            "status": "failed",
            "stage": "idle",
            "message": "No student images available for training",
        }

    created = repository.create_training_run(
        status="running",
        stage="queued",
        message=f"Queued with epochs={epochs}, batch_size={batch_size}",
        requested_epochs=epochs,
        requested_batch_size=batch_size,
        dataset_size=dataset_size,
    )

    _active_run_id = created["id"]

    logger.info(f"Training started: {_active_run_id}")

    return {
        "status": "running",
        "stage": "queued",
        "run_id": created["id"],
        "message": created["message"],
        "requested_epochs": created.get("requested_epochs"),
        "requested_batch_size": created.get("requested_batch_size"),
        "dataset_size": created.get("dataset_size"),
        "progress_percent": created.get("progress_percent", 0.0),
        "remote_provider": created.get("remote_provider"),
        "remote_status": created.get("remote_status"),
    }


def update_training_stage(
    run_id: str,
    stage: str,
    message: str,
    progress_percent: float | None = None,
    remote_status: str | None = None,
) -> None:
    if not run_id:
        return

    repository.update_training_run(
        run_id,
        status="running",
        stage=stage,
        message=message,
        progress_percent=progress_percent,
        remote_status=remote_status,
    )

    logger.info(f"Training stage updated: {stage}")


def set_training_remote_job(run_id: str, remote_job_id: str) -> None:
    if not run_id or not remote_job_id:
        return

    repository.set_training_remote_job(run_id=run_id, remote_job_id=remote_job_id)
    logger.info(f"Training remote job registered: run_id={run_id}, remote_job_id={remote_job_id}")


def complete_training(
    run_id: str,
    model_version: str,
    artifact_url: str | None = None,
    artifact_revision: str | None = None,
    metrics: dict | None = None,
    completion_message: str | None = None,
) -> None:
    global _active_run_id

    repository.update_training_run(
        run_id,
        status="completed",
        stage="completed",
        message=completion_message or "Training completed successfully.",
        model_version=model_version,
        progress_percent=100.0,
        remote_status="completed",
        artifact_url=artifact_url,
        artifact_revision=artifact_revision,
        error_detail="",
    )

    if artifact_url:
        repository.create_training_artifact(
            run_id=run_id,
            artifact_type="vggface",
            artifact_name="vggface_artifact",
            artifact_url=artifact_url,
            artifact_revision=artifact_revision,
            metrics_json=json.dumps(metrics) if metrics else None,
        )

    logger.info(f"Training completed: {run_id}")

    repository.set_attendance_lock(False, "")

    _active_run_id = None


def fail_training(run_id: str, error_message: str, error_detail: str | None = None) -> None:
    global _active_run_id

    repository.update_training_run(
        run_id,
        status="failed",
        stage="failed",
        message=error_message,
        remote_status="failed",
        error_detail=error_detail or error_message,
    )

    logger.error(f"Training failed: {error_message}")

    _active_run_id = None


def latest_training_status() -> dict:
    run = repository.latest_training_run()

    if not run:
        return {
            "status": "idle",
            "stage": "idle",
            "message": "No training run found",
        }

    artifact = repository.latest_training_artifact(run["id"])
    if artifact:
        if not run.get("artifact_url"):
            run["artifact_url"] = artifact.get("artifact_url")
        if not run.get("artifact_revision"):
            run["artifact_revision"] = artifact.get("artifact_revision")

        metrics_json = artifact.get("metrics_json")
        if isinstance(metrics_json, str) and metrics_json.strip():
            try:
                run["metrics"] = json.loads(metrics_json)
            except json.JSONDecodeError:
                run["metrics"] = {"raw": metrics_json}

    return run