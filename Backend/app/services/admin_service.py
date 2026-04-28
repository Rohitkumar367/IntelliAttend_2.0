from __future__ import annotations

import logging

from app.core.config import settings
from app.db import repository
from app.services.cloudinary_service import delete_folder_assets
from app.services.embedding_service import rebuild_embeddings

logger = logging.getLogger(__name__)


def reset_semester() -> dict:
    logger.warning("⚠️ Reset semester started")

    try:
        delete_folder_assets(settings.cloudinary_folder)
        logger.info("Cloudinary assets deleted")
    except Exception as e:
        logger.error(f"Cloudinary cleanup failed: {e}")

    try:
        repository.clear_all_data()
        logger.info("Database cleared")
    except Exception as e:
        logger.error(f"Database cleanup failed: {e}")

    try:
        if settings.embeddings_path.exists():
            settings.embeddings_path.unlink(missing_ok=True)
            logger.info("Embeddings file removed")
    except Exception as e:
        logger.error(f"Embeddings cleanup failed: {e}")

    logger.warning("⚠️ Reset semester completed")

    repository.set_attendance_lock(
        True,
        "Student dataset changed. Retrain model to enable attendance marking.",
    )

    return {"status": "reset_complete"}


def rebuild_embeddings_now() -> dict:
    logger.info("Manual embeddings rebuild triggered")
    result = rebuild_embeddings()
    repository.set_attendance_lock(False, "")
    return result