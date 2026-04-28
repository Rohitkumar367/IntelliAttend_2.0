from __future__ import annotations

import logging
import time
from typing import Iterable

import cloudinary
import cloudinary.api
import cloudinary.uploader

from app.core.config import settings

logger = logging.getLogger(__name__)

_configured = False


def configure_cloudinary() -> None:
    global _configured
    if _configured:
        return

    if not (
        settings.cloudinary_cloud_name
        and settings.cloudinary_api_key
        and settings.cloudinary_api_secret
    ):
        raise RuntimeError("Cloudinary credentials are missing")

    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )

    _configured = True
    logger.info("Cloudinary configured")


def upload_image_bytes(image_bytes: bytes, public_id: str) -> dict[str, str]:
    configure_cloudinary()

    try:
        result = cloudinary.uploader.upload(
            image_bytes,
            folder=settings.cloudinary_folder,
            public_id=public_id,
            overwrite=True,
            resource_type="image",
        )
        logger.info(f"Uploaded image: {result['public_id']}")
        return {
            "public_id": result["public_id"],
            "url": result["secure_url"],
        }

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise


def delete_by_public_ids(public_ids: Iterable[str]) -> None:
    ids = [x for x in public_ids if x]
    if not ids:
        return

    configure_cloudinary()

    chunk_size = 20
    deleted_count = 0

    for start in range(0, len(ids), chunk_size):
        chunk = ids[start : start + chunk_size]

        for attempt in range(3):
            try:
                cloudinary.api.delete_resources(chunk, resource_type="image")
                deleted_count += len(chunk)
                break
            except Exception as e:
                message = str(e)
                is_timeout = "420" in message or "Timeout waiting for parallel processing" in message

                if is_timeout and attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
                    continue

                logger.error(f"Delete failed for batch: {e}")
                raise

    logger.info(f"Deleted {deleted_count} images")


def delete_folder_assets(folder_prefix: str | None = None) -> None:
    configure_cloudinary()

    prefix = folder_prefix or settings.cloudinary_folder
    next_cursor = None

    while True:
        result = cloudinary.api.resources(
            type="upload",
            resource_type="image",
            prefix=prefix,
            max_results=100,
            next_cursor=next_cursor,
        )

        resources = result.get("resources", [])
        ids = [r.get("public_id") for r in resources if r.get("public_id")]

        if ids:
            cloudinary.api.delete_resources(ids, resource_type="image")
            logger.info(f"Deleted batch of {len(ids)} images")

        next_cursor = result.get("next_cursor")
        if not next_cursor:
            break