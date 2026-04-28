from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services.student_service import (
    create_student_with_images,
    delete_student,
    delete_student_by_roll,
    list_students,
)

# ------------------ Config ------------------
router = APIRouter(prefix="/students", tags=["students"])
logger = logging.getLogger(__name__)


# ------------------ Get Students ------------------
@router.get("")
def get_students() -> list[dict]:
    return list_students()


# ------------------ Add Student ------------------
@router.post("")
async def add_student(
    name: str = Form(...),
    roll_no: str | None = Form(default=None),
    images: list[UploadFile] = File(default=[]),
) -> dict:
    try:
        if not images:
            raise HTTPException(status_code=400, detail="At least one image required")

        if len(images) > 50:
            raise HTTPException(status_code=400, detail="Max 50 images allowed")

        for img in images:
            if not img.content_type or not img.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="Invalid file type")

        logger.info(f"Adding student: {name}")

        created = create_student_with_images(
            name=name,
            roll_no=roll_no,
            files=images,
        )

        return created

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ------------------ Delete Student ------------------
@router.delete("/{student_id}")
async def remove_student(student_id: str) -> dict:
    logger.info(f"Deleting student: {student_id}")

    success = delete_student(student_id)
    if not success:
        raise HTTPException(status_code=404, detail="Student not found")

    return {"status": "deleted", "student_id": student_id}


#------------------- Delete Student by enroll no -------
@router.delete("/by-roll/{roll_no}")
async def remove_student_by_roll(roll_no: str) -> dict:
    logger.info(f"Deleting student by roll_no: {roll_no}")

    success = delete_student_by_roll(roll_no)

    if not success:
        raise HTTPException(status_code=404, detail="Student not found")

    return {"status": "deleted", "roll_no": roll_no}