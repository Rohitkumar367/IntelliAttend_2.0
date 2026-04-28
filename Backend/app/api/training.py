from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.payloads import TrainRequest
from app.services.remote_training_service import ensure_remote_training_configured
from app.services.training_service import latest_training_status, start_training
from app.workers.tasks import run_training_pipeline_async

# ------------------ Config ------------------
router = APIRouter(prefix="/training", tags=["training"])
logger = logging.getLogger(__name__)


# ------------------ Start Training ------------------
@router.post("/start")
def start(payload: TrainRequest) -> dict:
    if payload.epochs != 25:
        raise HTTPException(status_code=400, detail="Epochs must be 25")

    if payload.batch_size not in {4, 8, 16}:
        raise HTTPException(status_code=400, detail="Batch size must be one of: 4, 8, 16")

    try:
        ensure_remote_training_configured()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info(f"Training start requested: epochs={payload.epochs}, batch={payload.batch_size}")

    started = start_training(
        epochs=payload.epochs,
        batch_size=payload.batch_size,
    )

    if (started.get("run_id") and started.get("status") == "running" and not started.get("already_running")):
        try:
            run_training_pipeline_async(
                started["run_id"],
                payload.epochs,
                payload.batch_size,
            )
        except Exception as e:
            logger.error(f"Failed to start async training: {e}")

    return started


# ------------------ Training Status ------------------
@router.get("/status")
def status() -> dict:
    return latest_training_status()