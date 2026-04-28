from datetime import date, time
from pydantic import BaseModel, Field


# ------------------ Response Models ------------------

class AttendanceRecognizeResponse(BaseModel):
    name: str
    student_id: str | None
    confidence: float


class MultiFaceResponse(BaseModel):
    total_faces: int
    recognized_faces: int
    results: list[AttendanceRecognizeResponse]
    marked: list[dict]


class TrainingStatusResponse(BaseModel):
    id: str | None = None
    status: str
    stage: str | None = None
    message: str
    model_version: str | None = None
    requested_epochs: int | None = None
    requested_batch_size: int | None = None
    dataset_size: int | None = None
    progress_percent: float | None = None
    remote_job_id: str | None = None
    remote_provider: str | None = None
    remote_status: str | None = None
    error_detail: str | None = None
    artifact_url: str | None = None
    artifact_revision: str | None = None
    metrics: dict | None = None


# ------------------ Request Models ------------------

class StudentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    roll_no: str | None = None


class AttendanceImportItem(BaseModel):
    student_id: str = Field(min_length=1)
    date: date
    time: time
    confidence: float | None = Field(default=None, ge=0, le=1)
    source: str = "local_client"


class AttendanceImportRequest(BaseModel):
    items: list[AttendanceImportItem]


class TrainRequest(BaseModel):
    epochs: int = Field(default=25, gt=0)
    batch_size: int = Field(default=8, gt=0)


class ClassDayRequest(BaseModel):
    date: date
    is_class_day: bool = True