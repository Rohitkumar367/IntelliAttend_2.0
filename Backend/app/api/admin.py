from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, status

from app.core.config import settings
from app.services.admin_service import rebuild_embeddings_now, reset_semester

# ------------------ Logging ------------------
logger = logging.getLogger(__name__)

# ------------------ Router ------------------
router = APIRouter(prefix="/admin", tags=["admin"])


# ------------------ Reset Semester ------------------
@router.delete("/reset-semester")
def reset(x_confirm_token: str | None = Header(default=None)) -> dict:
    if x_confirm_token != settings.reset_confirm_token:
        logger.warning("Unauthorized reset attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing or invalid confirmation token",
        )

    logger.info("Reset semester triggered")
    reset_semester()

    return {"status": "reset_complete"}


# ------------------ Rebuild Embeddings ------------------
@router.post("/rebuild-embeddings")
def rebuild_embeddings_endpoint() -> dict:
    logger.info("Manual embeddings rebuild triggered")

    result = rebuild_embeddings_now()

    logger.info(f"Embeddings rebuilt: {result.get('samples', 0)} samples")

    return result