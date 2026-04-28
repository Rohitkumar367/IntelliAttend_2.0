from __future__ import annotations

import logging
import shutil
from datetime import datetime

import cv2
import numpy as np
import requests
import mediapipe as mp
from mediapipe.python.solutions import face_detection as mp_face_detection
from keras_facenet import FaceNet

from app.core.config import settings
from app.db import repository

# ------------------ Logging ------------------
logger = logging.getLogger(__name__)

# ------------------ Globals ------------------
_embedder: FaceNet | None = None
_cached_embeddings: np.ndarray | None = None
_cached_labels: np.ndarray | None = None
_cached_student_ids: np.ndarray | None = None

UNKNOWN_RESPONSE = {
    "name": "Unknown",
    "student_id": None,
    "confidence": 0.0,
}


def _is_student_available(student_id: str | None) -> bool:
    if not student_id:
        return False

    try:
        return repository.get_student(str(student_id)) is not None
    except Exception:
        return False


def _hf_embeddings_configured() -> bool:
    return bool(settings.hf_token and settings.hf_model_repo_id and settings.hf_embeddings_artifact_path)


def _download_embeddings_from_hf() -> bool:
    if not _hf_embeddings_configured():
        return False

    try:
        from huggingface_hub import hf_hub_download  # pyright: ignore[reportMissingImports]
    except Exception as exc:
        logger.warning(f"huggingface_hub not available for embeddings download: {exc}")
        return False

    try:
        downloaded_path = hf_hub_download(
            repo_id=settings.hf_model_repo_id,
            repo_type="model",
            filename=settings.hf_embeddings_artifact_path,
            revision=settings.hf_embeddings_ref,
            token=settings.hf_token,
        )

        settings.local_models_root.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(downloaded_path, settings.embeddings_path)
        logger.info(f"Embeddings downloaded from HF: {settings.hf_model_repo_id}/{settings.hf_embeddings_artifact_path}")
        return True
    except Exception as exc:
        logger.warning(f"Failed to download embeddings from HF: {exc}")
        return False


def _upload_embeddings_to_hf() -> str | None:
    if not _hf_embeddings_configured():
        return None

    if not settings.embeddings_path.exists():
        return None

    try:
        from huggingface_hub import HfApi  # pyright: ignore[reportMissingImports]
    except Exception as exc:
        logger.warning(f"huggingface_hub not available for embeddings upload: {exc}")
        return None

    try:
        api = HfApi(token=settings.hf_token)
        api.create_repo(
            repo_id=settings.hf_model_repo_id,
            repo_type="model",
            private=settings.hf_private_repo,
            exist_ok=True,
        )

        commit = api.upload_file(
            repo_id=settings.hf_model_repo_id,
            repo_type="model",
            path_or_fileobj=str(settings.embeddings_path),
            path_in_repo=settings.hf_embeddings_artifact_path,
            commit_message="Update embeddings artifact",
        )

        revision = getattr(commit, "oid", None)
        logger.info(
            "Embeddings uploaded to HF repo %s at %s",
            settings.hf_model_repo_id,
            settings.hf_embeddings_artifact_path,
        )
        return str(revision) if revision else None
    except Exception as exc:
        logger.warning(f"Failed to upload embeddings to HF: {exc}")
        return None

# ------------------ Embedder ------------------
def _get_embedder() -> FaceNet:
    global _embedder
    if _embedder is None:
        logger.info("Loading FaceNet model...")
        _embedder = FaceNet()
    return _embedder


# ------------------ Image Utils ------------------
def _decode_image(data: bytes) -> np.ndarray | None:
    arr = np.frombuffer(data, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)

_mp_face = mp_face_detection.FaceDetection(
    model_selection=0,
    min_detection_confidence=0.5,
)

def _detect_face(image: np.ndarray) -> np.ndarray | None:
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = _mp_face.process(rgb)
    detections = getattr(results, "detections", None)

    if not detections:
        logger.warning("No face detected")
        return None

    detection = detections[0]
    bbox = detection.location_data.relative_bounding_box

    h, w, _ = image.shape
    x, y = int(bbox.xmin * w), int(bbox.ymin * h)
    bw, bh = int(bbox.width * w), int(bbox.height * h)

    # ✅ safety fix
    x = max(0, x)
    y = max(0, y)
    bw = min(w - x, bw)
    bh = min(h - y, bh)

    return image[y:y+bh, x:x+bw]

def detect_multiple_faces(image: np.ndarray) -> list[np.ndarray]:
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = _mp_face.process(rgb)
    detections = getattr(results, "detections", None)

    if not detections:
        return []

    faces = []
    h, w, _ = image.shape

    for detection in detections:
        bbox = detection.location_data.relative_bounding_box

        x, y = int(bbox.xmin * w), int(bbox.ymin * h)
        bw, bh = int(bbox.width * w), int(bbox.height * h)

        # safety fix
        x = max(0, x)
        y = max(0, y)
        bw = min(w - x, bw)
        bh = min(h - y, bh)

        faces.append(image[y:y+bh, x:x+bw])

    return faces

def _embedding_from_bgr(image_bgr: np.ndarray) -> np.ndarray:
    image_rgb = cv2.cvtColor(cv2.resize(image_bgr, (160, 160)), cv2.COLOR_BGR2RGB)
    emb = _get_embedder().embeddings([image_rgb])[0]
    norm = np.linalg.norm(emb)
    return emb if norm == 0 else emb / norm


# ------------------ Embedding Build ------------------
def rebuild_embeddings() -> dict[str, str | int]:
    logger.info("Rebuilding embeddings...")

    rows = repository.list_all_images()
    embeddings: list[np.ndarray] = []
    labels: list[str] = []
    student_ids: list[str] = []

    for row in rows:
        try:
            response = requests.get(row["url"], timeout=10)
            response.raise_for_status()

            image = _decode_image(response.content)
            if image is None:
                continue

            face = _detect_face(image)
            if face is None:
                continue

            emb = _embedding_from_bgr(face)

            embeddings.append(emb)
            labels.append(row["student_name"])
            student_ids.append(row["student_id"])

        except Exception as e:
            logger.warning(f"Failed processing image {row['url']}: {e}")
            continue

    settings.local_models_root.mkdir(parents=True, exist_ok=True)

    np.savez(
        settings.embeddings_path,
        embeddings=np.array(embeddings),
        labels=np.array(labels),
        student_ids=np.array(student_ids),
        generated_at=datetime.utcnow().isoformat(),
    )

    _refresh_cache()

    hf_revision = _upload_embeddings_to_hf()

    logger.info(f"Embeddings rebuilt: {len(embeddings)} samples")

    return {
        "status": "ok",
        "samples": len(embeddings),
        "artifact": str(settings.embeddings_path),
        "hf_revision": hf_revision or "",
    }


# ------------------ Cache ------------------
def _refresh_cache() -> None:
    global _cached_embeddings, _cached_labels, _cached_student_ids

    if not settings.embeddings_path.exists():
        _cached_embeddings = np.array([])
        _cached_labels = np.array([])
        _cached_student_ids = np.array([])
        return

    try:
        loaded = np.load(settings.embeddings_path, allow_pickle=True)

        _cached_embeddings = loaded.get("embeddings", np.array([]))
        _cached_labels = loaded.get("labels", np.array([]))
        _cached_student_ids = loaded.get("student_ids", np.array([]))

        logger.info("Model loaded into memory")

    except Exception as e:
        logger.error(f"Failed to load embeddings: {e}")
        _cached_embeddings = np.array([])
        _cached_labels = np.array([])
        _cached_student_ids = np.array([])


def ensure_embeddings_loaded() -> None:
    global _cached_embeddings

    if _cached_embeddings is None:
        if not settings.embeddings_path.exists():
            _download_embeddings_from_hf()
        _refresh_cache()

    if _cached_embeddings is None or len(_cached_embeddings) == 0:
        if _download_embeddings_from_hf():
            _refresh_cache()

    if _cached_embeddings is None or len(_cached_embeddings) == 0:
        logger.warning("Embeddings empty, rebuilding...")
        rebuild_embeddings()


# ------------------ Recognition ------------------
def recognize_image_bytes(image_bytes: bytes) -> dict[str, str | float | None]:
    ensure_embeddings_loaded()

    if _cached_embeddings is None or len(_cached_embeddings) == 0:
        return UNKNOWN_RESPONSE

    if _cached_labels is None or len(_cached_labels) == 0:
        return UNKNOWN_RESPONSE

    if _cached_student_ids is None or len(_cached_student_ids) == 0:
        return UNKNOWN_RESPONSE

    image = _decode_image(image_bytes)
    if image is None:
        return UNKNOWN_RESPONSE

    face = _detect_face(image)
    if face is None:
        return UNKNOWN_RESPONSE

    emb = _embedding_from_bgr(face)

    sims = np.dot(_cached_embeddings, emb)
    idx = int(np.argmax(sims))
    score = float(sims[idx])
    score = max(0.0, min(1.0, score))

    if score < settings.embedding_threshold:
        return {"name": "Unknown", "student_id": None, "confidence": score}

    predicted_id = str(_cached_student_ids[idx])
    if not _is_student_available(predicted_id):
        return {"name": "Unknown", "student_id": None, "confidence": score}

    return {
        "name": str(_cached_labels[idx]),
        "student_id": predicted_id,
        "confidence": score,
    }

def recognize_multiple_faces(image_bytes: bytes) -> list[dict]:
    ensure_embeddings_loaded()

    if _cached_embeddings is None or len(_cached_embeddings) == 0:
        return []

    if _cached_labels is None or len(_cached_labels) == 0:
        return []

    if _cached_student_ids is None or len(_cached_student_ids) == 0:
        return []

    image = _decode_image(image_bytes)
    if image is None:
        return []

    faces = detect_multiple_faces(image)

    results = []

    for face in faces:
        emb = _embedding_from_bgr(face)

        sims = _cached_embeddings @ emb
        idx = int(np.argmax(sims))

        if idx >= len(_cached_labels) or idx >= len(_cached_student_ids):
            results.append({
                "name": "Unknown",
                "student_id": None,
                "confidence": 0.0,
            })
            continue

        score = float(sims[idx])
        score = max(0.0, min(1.0, score))

        if score < settings.embedding_threshold:
            results.append({
                "name": "Unknown",
                "student_id": None,
                "confidence": score,
            })
        else:
            predicted_id = str(_cached_student_ids[idx])
            if not _is_student_available(predicted_id):
                results.append({
                    "name": "Unknown",
                    "student_id": None,
                    "confidence": score,
                })
                continue

            results.append({
                "name": str(_cached_labels[idx]),
                "student_id": predicted_id,
                "confidence": score,
            })

    return results