from __future__ import annotations

import logging
from uuid import uuid4

import cv2
import numpy as np
from fastapi import UploadFile

from app.db import repository
from app.services.embedding_service import detect_multiple_faces
from app.services.cloudinary_service import delete_by_public_ids, upload_image_bytes

logger = logging.getLogger(__name__)

MAX_CAPTURE_IMAGES = 50
MAX_STORED_IMAGES = 40
SIMILAR_HASH_DISTANCE = 2


def _average_hash(image_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (8, 8))
    mean = resized.mean()
    return (resized > mean).astype(np.uint8).flatten()


def _hamming_distance(a: np.ndarray, b: np.ndarray) -> int:
    return int(np.count_nonzero(a != b))


def _score_image(image_bgr: np.ndarray) -> float:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    sharpness_score = min(sharpness / 300.0, 1.0)

    brightness = float(gray.mean())
    brightness_score = max(0.0, 1.0 - abs(brightness - 128.0) / 128.0)

    h, w = gray.shape
    size_score = min((h * w) / (640.0 * 480.0), 1.0)

    return (0.5 * sharpness_score) + (0.3 * brightness_score) + (0.2 * size_score)


def _prepare_candidate(image_bytes: bytes) -> dict | None:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    image_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image_bgr is None:
        return None

    faces = detect_multiple_faces(image_bgr)
    if not faces:
        return None

    largest_face = max(faces, key=lambda face: face.shape[0] * face.shape[1])
    image_hash = _average_hash(largest_face)
    score = _score_image(largest_face)

    return {"score": score, "hash": image_hash}


def list_students() -> list[dict]:
    return repository.list_students()


def create_student_with_images(
    name: str,
    roll_no: str | None,
    files: list[UploadFile],
) -> dict:

    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError("Student name cannot be empty")

    if len(files) == 0:
        raise ValueError("At least one image is required")

    if len(files) > MAX_CAPTURE_IMAGES:
        raise ValueError(f"Max {MAX_CAPTURE_IMAGES} images allowed")

    logger.info(f"Creating student: {cleaned_name}")

    student = repository.create_student(cleaned_name, roll_no)
    uploaded: list[dict[str, str]] = []
    candidates: list[dict] = []

    try:
        for idx, upload in enumerate(files):

            if not upload.content_type or not upload.content_type.startswith("image/"):
                continue

            image_bytes = upload.file.read()
            if not image_bytes:
                continue

            prepared = _prepare_candidate(image_bytes)
            if not prepared:
                continue

            candidates.append(
                {
                    "source_index": idx,
                    "image_bytes": image_bytes,
                    "score": prepared["score"],
                    "hash": prepared["hash"],
                }
            )

        if not candidates:
            repository.delete_student(student["id"])
            raise ValueError("No valid face images uploaded")

        candidates.sort(key=lambda item: item["score"], reverse=True)

        selected: list[dict] = []
        for candidate in candidates:
            is_too_similar = any(
                _hamming_distance(candidate["hash"], picked["hash"]) <= SIMILAR_HASH_DISTANCE
                for picked in selected
            )
            if is_too_similar:
                continue

            selected.append(candidate)
            if len(selected) >= MAX_STORED_IMAGES:
                break

        if not selected:
            selected = candidates[:MAX_STORED_IMAGES]

        for candidate in selected:
            public_id = f"{student['id']}_{candidate['source_index']}_{uuid4().hex[:8]}"

            result = upload_image_bytes(
                image_bytes=candidate["image_bytes"],
                public_id=public_id
            )

            uploaded.append(result)

        if not uploaded:
            repository.delete_student(student["id"])
            raise ValueError("No valid images uploaded")

        repository.replace_student_images(student["id"], uploaded)
        repository.set_attendance_lock(
            True,
            "Student dataset changed. Retrain model to enable attendance marking.",
        )

        return {
            **student,
            "captured_images": len(files),
            "valid_face_images": len(candidates),
            "stored_images": len(uploaded),
            "uploaded_images": len(uploaded),
            "embedding_status": "pending_training",
        }

    except Exception as e:
        logger.error(f"Student creation failed: {e}")

        if uploaded:
            try:
                delete_by_public_ids([item["public_id"] for item in uploaded])
            except Exception as cleanup_err:
                logger.error(f"Cloudinary cleanup failed: {cleanup_err}")

        repository.delete_student(student["id"])

        raise


def delete_student(student_id: str) -> bool:
    logger.info(f"Deleting student: {student_id}")

    student = repository.get_student(student_id)
    if not student:
        return False

    images = repository.student_images(student_id)

    delete_by_public_ids([item["public_id"] for item in images])

    repository.delete_student(student_id)
    repository.set_attendance_lock(
        True,
        "Student dataset changed. Retrain model to enable attendance marking.",
    )

    return True


def delete_student_by_roll(roll_no: str) -> bool:
    student = repository.get_student_by_roll(roll_no)

    if not student:
        return False

    student_id = student["id"]

    images = repository.student_images(student_id)

    delete_by_public_ids([item["public_id"] for item in images])

    repository.delete_student(student_id)
    repository.set_attendance_lock(
        True,
        "Student dataset changed. Retrain model to enable attendance marking.",
    )

    return True