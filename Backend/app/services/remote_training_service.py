from __future__ import annotations

import logging
from typing import Any

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


def ensure_remote_training_configured() -> None:
    missing: list[str] = []

    if not settings.hf_token:
        missing.append("HF_TOKEN")
    if not settings.hf_model_repo_id:
        missing.append("HF_MODEL_REPO_ID")
    if not settings.hf_space_id:
        missing.append("HF_SPACE_ID")
    if not settings.hf_space_api_url:
        missing.append("HF_SPACE_API_URL")

    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"Missing Hugging Face training configuration: {joined}")


def _join_space_url(path: str) -> str:
    base = settings.hf_space_api_url.rstrip("/")
    suffix = path if path.startswith("/") else f"/{path}"
    return f"{base}{suffix}"


def _auth_headers() -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {settings.hf_token}",
        "Content-Type": "application/json",
    }
    if settings.hf_callback_secret:
        headers["X-Callback-Secret"] = settings.hf_callback_secret
    return headers


def launch_hf_training_job(
    run_id: str,
    epochs: int,
    batch_size: int,
    images_manifest: list[dict[str, str]],
) -> dict[str, Any]:
    ensure_remote_training_configured()

    payload = {
        "run_id": run_id,
        "epochs": epochs,
        "batch_size": batch_size,
        "model_repo_id": settings.hf_model_repo_id,
        "space_id": settings.hf_space_id,
        "artifact_subdir": settings.hf_artifact_subdir,
        "private_repo": settings.hf_private_repo,
        "images": images_manifest,
    }

    if settings.hf_org_name:
        payload["org_name"] = settings.hf_org_name
    if settings.hf_dataset_repo_id:
        payload["dataset_repo_id"] = settings.hf_dataset_repo_id

    endpoint = _join_space_url(settings.hf_space_train_path)
    response = requests.post(
        endpoint,
        json=payload,
        headers=_auth_headers(),
        timeout=90,
    )
    response.raise_for_status()

    data = response.json()
    job_id = data.get("job_id")
    if not job_id:
        raise RuntimeError("Remote trainer did not return job_id")

    logger.info(f"Remote HF training submitted: run_id={run_id}, job_id={job_id}")
    return data


def get_hf_training_status(job_id: str) -> dict[str, Any]:
    ensure_remote_training_configured()

    status_path = settings.hf_space_status_path_template.format(job_id=job_id)
    endpoint = _join_space_url(status_path)
    response = requests.get(endpoint, headers=_auth_headers(), timeout=60)
    response.raise_for_status()

    data = response.json()
    progress = data.get("progress")
    if isinstance(progress, (int, float)):
        data["progress"] = max(0.0, min(100.0, float(progress)))

    return data
