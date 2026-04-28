from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, File, UploadFile, HTTPException, status

from app.schemas.payloads import AttendanceImportRequest, ClassDayRequest
from app.db import repository
from app.services.attendance_service import (
    import_attendance,
    mark_attendance_for_recognition,
    semester_summary_from_anchor,
    upsert_class_day,
)
from app.services.embedding_service import recognize_multiple_faces
from app.core.config import settings

# ------------------ Config ------------------
router = APIRouter(prefix="/attendance", tags=["attendance"])
logger = logging.getLogger(__name__)

THRESHOLD = settings.embedding_threshold


# ------------------ Import Attendance ------------------
@router.post("/import")
def import_logs(payload: AttendanceImportRequest) -> dict:
    try:
        inserted = import_attendance([item.model_dump() for item in payload.items])
        return {"success": True, "inserted": inserted}
    except Exception as e:
        logger.error(f"Import failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import attendance",
        )


# ------------------ Recognize Attendance (MULTI-FACE) ------------------
@router.post("/recognize")
async def recognize(image: UploadFile = File(...)) -> dict:
    try:
        # Validate file type
        if not image.content_type or not image.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type",
            )

        # Read image
        data = await image.read()

        # Validate size (max 5MB)
        if len(data) > 5 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image too large (max 5MB)",
            )

        # Run multi-face recognition
        results = recognize_multiple_faces(data)
        logger.info(f"Recognition results: {results}")

        lock_state = repository.get_attendance_lock_state()
        if lock_state.get("locked"):
            reason = str(lock_state.get("reason") or "Retrain model to enable attendance marking.")
            unknown_results = [
                {
                    "name": "Unknown",
                    "student_id": None,
                    "confidence": float(item.get("confidence") or 0.0),
                }
                for item in results
            ]

            return {
                "success": True,
                "attendance_enabled": False,
                "message": reason,
                "total_faces": len(unknown_results),
                "recognized_faces": 0,
                "results": unknown_results,
                "marked": [],
            }

        marked_students = []

        for result in results:
            student_id = result.get("student_id")
            confidence = result.get("confidence")

            # Apply threshold
            if student_id and confidence is not None and confidence >= THRESHOLD:
                marked = mark_attendance_for_recognition(
                    student_id=str(student_id),
                    confidence=float(confidence),
                )

                marked_students.append({
                    "student_id": student_id,
                    "confidence": confidence,
                    "attendance_marked": bool(marked),
                })

        # Final response
        return {
            "success": True,
            "attendance_enabled": True,
            "message": "Attendance marking active.",
            "total_faces": len(results),
            "recognized_faces": len(marked_students),
            "results": results,
            "marked": marked_students,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recognition failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Recognition failed",
        )


# ------------------ Class Day ------------------
@router.post("/class-day")
def class_day(payload: ClassDayRequest) -> dict:
    try:
        upsert_class_day(payload.date, payload.is_class_day)
        return {
            "success": True,
            "date": str(payload.date),
            "is_class_day": payload.is_class_day,
        }
    except Exception as e:
        logger.error(f"Class day update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update class day",
        )


@router.get("/lock-state")
def attendance_lock_state() -> dict:
    try:
        state = repository.get_attendance_lock_state()
        locked = bool(state.get("locked", False))
        reason = str(state.get("reason") or "")

        return {
            "success": True,
            "attendance_enabled": not locked,
            "locked": locked,
            "message": reason if locked else "Attendance marking active.",
        }
    except Exception as e:
        logger.error(f"Attendance lock state fetch failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch attendance lock state",
        )


# ------------------ Monthly Summary ------------------
@router.get("/monthly-summary")
def summary(year: int | None = None, month: int | None = None) -> dict:
    try:
        now = datetime.now()
        anchor_year = year or now.year
        months_count = month or 1

        if months_count < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="month must be at least 1",
            )

        if months_count > 24:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="month cannot exceed 24",
            )

        data = semester_summary_from_anchor(
            anchor_year=anchor_year,
            anchor_month=now.month,
            months_count=months_count,
        )

        return {
            "success": True,
            "year": anchor_year,
            "month": months_count,
            "items": data,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Monthly summary failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch monthly summary",
        )