from __future__ import annotations

import math
import logging
from datetime import date, datetime

from app.db import repository

logger = logging.getLogger(__name__)


# ------------------ Import Attendance ------------------
def import_attendance(items: list[dict]) -> int:
    inserted = 0

    for item in items:
        student_id = item.get("student_id")
        if not student_id:
            continue

        success = repository.add_attendance(
            student_id=student_id,
            day=item["date"],
            attended_at=item["time"],
            confidence=item.get("confidence"),
            source=item.get("source", "local_client"),
        )

        if success:
            inserted += 1

    logger.info(f"Imported attendance: {inserted} records")
    return inserted


# ------------------ Recognition Attendance ------------------
def mark_attendance_for_recognition(
    student_id: str,
    confidence: float,
    source: str = "webcam"
) -> bool:

    if not student_id:
        raise ValueError("Invalid student_id")

    if (
        not isinstance(confidence, (int, float))
        or math.isnan(confidence)
        or math.isinf(confidence)
    ):
        raise ValueError("Invalid confidence score")

    # Optional clamp instead of crash
    confidence = max(0.0, min(1.0, confidence))

    # Recognized ID may be stale if embeddings were built before student deletion.
    if repository.get_student(student_id) is None:
        logger.info(f"Skipping attendance for missing student: {student_id}")
        return False

    today = date.today()

    # Optional: check class day
    if not repository.is_class_day(today):
        logger.info("Not a class day, skipping attendance")
        return False

    try:
        success = repository.add_attendance(
            student_id=student_id,
            day=today,
            attended_at=datetime.now().time().replace(microsecond=0).isoformat(),
            confidence=confidence,
            source=source,
        )
    except Exception as exc:
        logger.warning(f"Attendance insert skipped for student {student_id}: {exc}")
        return False

    if success:
        logger.info(f"Attendance marked for {student_id}")
    else:
        logger.info(f"Attendance already exists for {student_id}")

    return success


# ------------------ Class Day ------------------
def upsert_class_day(day: date, is_class_day: bool) -> None:
    repository.upsert_class_day(day, is_class_day)
    logger.info(f"Class day updated: {day} -> {is_class_day}")


# ------------------ Monthly Summary ------------------
def monthly_summary(year: int, month: int) -> list[dict]:
    return repository.monthly_summary(year, month)


def semester_summary_from_anchor(anchor_year: int, anchor_month: int, months_count: int) -> list[dict]:
    if months_count < 1:
        raise ValueError("months_count must be at least 1")

    if anchor_month < 1 or anchor_month > 12:
        raise ValueError("anchor_month must be between 1 and 12")

    aggregate_map: dict[str, dict] = {}

    for offset in range(months_count):
        total_month_index = (anchor_year * 12) + (anchor_month - 1) - offset
        year = total_month_index // 12
        month = (total_month_index % 12) + 1

        items = repository.monthly_summary(year, month)

        for item in items:
            student_id = str(item.get("student_id", ""))
            if not student_id:
                continue

            current = aggregate_map.get(student_id)
            if current is None:
                current = {
                    "student_id": student_id,
                    "student_name": item.get("student_name", "Unknown"),
                    "present_days": 0,
                    "absent_days": 0,
                }

            current["present_days"] += int(item.get("present_days", 0) or 0)
            current["absent_days"] += int(item.get("absent_days", 0) or 0)
            aggregate_map[student_id] = current

    return sorted(aggregate_map.values(), key=lambda row: str(row.get("student_name", "")).lower())