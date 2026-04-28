from datetime import date, datetime
from pydantic import BaseModel, Field


class Student(BaseModel):
    id: str
    name: str
    roll_no: str | None = None
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AttendanceLog(BaseModel):
    id: str
    student_id: str
    date: date
    time: str
    confidence: float | None = None
    source: str = "local_client"


class TrainingRun(BaseModel):
    id: str
    status: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    model_version: str | None = None
    message: str | None = None
