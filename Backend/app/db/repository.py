from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

from app.db.session import get_conn


def list_students() -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id::text, name, roll_no, active, created_at::text FROM students ORDER BY created_at DESC")
            rows = cur.fetchall()
    return [
        {
            "id": row[0],
            "name": row[1],
            "roll_no": row[2],
            "active": row[3],
            "created_at": row[4],
        }
        for row in rows
    ]

def count_students() -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM students")
            return cur.fetchone()[0]


def count_images() -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM images")
            return cur.fetchone()[0]


def create_student(name: str, roll_no: str | None) -> dict[str, Any]:
    student_id = str(uuid4())
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO students(id, name, roll_no, active) VALUES (%s, %s, %s, TRUE)",
                (student_id, name, roll_no),
            )
            cur.execute("SELECT created_at::text FROM students WHERE id = %s", (student_id,))
            created_at = cur.fetchone()[0]

    return {
        "id": student_id,
        "name": name,
        "roll_no": roll_no,
        "active": True,
        "created_at": created_at,
    }


def get_student(student_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id::text, name, roll_no, active, created_at::text FROM students WHERE id = %s",
                (student_id,),
            )
            row = cur.fetchone()

    if not row:
        return None

    return {
        "id": row[0],
        "name": row[1],
        "roll_no": row[2],
        "active": row[3],
        "created_at": row[4],
    }


def get_student_by_roll(roll_no: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, roll_no FROM students WHERE roll_no = %s",
                (roll_no,)
            )
            row = cur.fetchone()

            if not row:
                return None

            return {
                "id": row[0],
                "name": row[1],
                "roll_no": row[2],
            }


def delete_student(student_id: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM students WHERE id = %s", (student_id,))


def add_student_image(student_id: str, public_id: str, url: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO images(id, student_id, public_id, url) VALUES (%s, %s, %s, %s)",
                (str(uuid4()), student_id, public_id, url),
            )


def replace_student_images(student_id: str, images: list[dict[str, str]]) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM images WHERE student_id = %s", (student_id,))
            for image in images:
                cur.execute(
                    "INSERT INTO images(id, student_id, public_id, url) VALUES (%s, %s, %s, %s)",
                    (str(uuid4()), student_id, image["public_id"], image["url"]),
                )


def student_images(student_id: str) -> list[dict[str, str]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT public_id, url FROM images WHERE student_id = %s ORDER BY created_at", (student_id,))
            rows = cur.fetchall()
    return [{"public_id": row[0], "url": row[1]} for row in rows]


def list_all_images() -> list[dict[str, str]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT i.student_id::text, s.name, i.public_id, i.url FROM images i JOIN students s ON s.id = i.student_id ORDER BY s.name"
            )
            rows = cur.fetchall()
    return [
        {
            "student_id": row[0],
            "student_name": row[1],
            "public_id": row[2],
            "url": row[3],
        }
        for row in rows
    ]


def add_attendance(student_id: str, day: date, attended_at: str, confidence: float | None, source: str) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO attendance(id, student_id, attended_on, attended_at, confidence, source)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT(student_id, attended_on) DO NOTHING
                RETURNING id
                """,
                (str(uuid4()), student_id, day.isoformat(), attended_at, confidence, source),
            )

            result = cur.fetchone()

    return result is not None


def upsert_class_day(day: date, is_class_day: bool) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO class_days(day, is_class_day)
                VALUES (%s, %s)
                ON CONFLICT(day) DO UPDATE SET is_class_day = EXCLUDED.is_class_day
                """,
                (day.isoformat(), is_class_day),
            )


def is_class_day(day: date) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT is_class_day FROM class_days WHERE day = %s",
                (day.isoformat(),),
            )
            row = cur.fetchone()

    # if not found, assume it's a class day
    return row[0] if row else True
    

def monthly_summary(year: int, month: int) -> list[dict[str, Any]]:
    month_prefix = f"{year:04d}-{month:02d}"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.id::text, s.name,
                       COUNT(DISTINCT a.attended_on) AS present_days
                FROM students s
                LEFT JOIN attendance a
                  ON a.student_id = s.id
                 AND a.attended_on::text LIKE %s
                GROUP BY s.id, s.name
                ORDER BY s.name
                """,
                (f"{month_prefix}-%",),
            )
            present_rows = cur.fetchall()

            cur.execute(
                "SELECT COUNT(*) FROM class_days WHERE is_class_day = TRUE AND day::text LIKE %s",
                (f"{month_prefix}-%",),
            )
            class_days_count = cur.fetchone()[0]

    inferred_class_days = 0
    if class_days_count:
        inferred_class_days = int(class_days_count)
    elif present_rows:
        inferred_class_days = max(int(row[2]) for row in present_rows)

    output: list[dict[str, Any]] = []
    for row in present_rows:
        present_days = int(row[2])
        absent_days = max(0, inferred_class_days - present_days) if inferred_class_days else 0
        output.append(
            {
                "student_id": row[0],
                "student_name": row[1],
                "present_days": present_days,
                "absent_days": absent_days,
            }
        )
    return output


def create_training_run(
    status: str,
    stage: str,
    message: str,
    requested_epochs: int | None = None,
    requested_batch_size: int | None = None,
    dataset_size: int | None = None,
) -> dict[str, Any]:
    run_id = str(uuid4())
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO training_runs(
                    id, status, stage, message,
                    requested_epochs, requested_batch_size, dataset_size,
                    progress_percent, remote_provider, remote_status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    run_id,
                    status,
                    stage,
                    message,
                    requested_epochs,
                    requested_batch_size,
                    dataset_size,
                    0.0,
                    "huggingface-space",
                    "queued",
                ),
            )
    return {
        "id": run_id,
        "status": status,
        "stage": stage,
        "message": message,
        "requested_epochs": requested_epochs,
        "requested_batch_size": requested_batch_size,
        "dataset_size": dataset_size,
        "progress_percent": 0.0,
        "remote_provider": "huggingface-space",
        "remote_status": "queued",
    }


def update_training_run(
    run_id: str,
    status: str,
    stage: str,
    message: str,
    model_version: str | None = None,
    progress_percent: float | None = None,
    remote_status: str | None = None,
    remote_job_id: str | None = None,
    remote_provider: str | None = None,
    error_detail: str | None = None,
    artifact_url: str | None = None,
    artifact_revision: str | None = None,
) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE training_runs
                   SET status = %s,
                       stage = %s,
                       message = %s,
                       model_version = COALESCE(%s, model_version),
                       progress_percent = COALESCE(%s, progress_percent),
                       remote_status = COALESCE(%s, remote_status),
                       remote_job_id = COALESCE(%s, remote_job_id),
                       remote_provider = COALESCE(%s, remote_provider),
                       error_detail = COALESCE(%s, error_detail),
                       artifact_url = COALESCE(%s, artifact_url),
                       artifact_revision = COALESCE(%s, artifact_revision),
                       completed_at = CASE WHEN %s IN ('completed', 'failed') THEN NOW() ELSE completed_at END
                 WHERE id = %s
                """,
                (
                    status,
                    stage,
                    message,
                    model_version,
                    progress_percent,
                    remote_status,
                    remote_job_id,
                    remote_provider,
                    error_detail,
                    artifact_url,
                    artifact_revision,
                    status,
                    run_id,
                ),
            )


def set_training_remote_job(run_id: str, remote_job_id: str, remote_provider: str = "huggingface-space") -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE training_runs
                   SET remote_job_id = %s,
                       remote_provider = %s,
                       remote_status = 'running'
                 WHERE id = %s
                """,
                (remote_job_id, remote_provider, run_id),
            )


def create_training_artifact(
    run_id: str,
    artifact_type: str,
    artifact_name: str,
    artifact_url: str,
    artifact_path: str | None = None,
    artifact_revision: str | None = None,
    metrics_json: str | None = None,
    checksum: str | None = None,
) -> dict[str, str | None]:
    artifact_id = str(uuid4())
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO training_artifacts(
                    id,
                    training_run_id,
                    artifact_type,
                    artifact_name,
                    artifact_url,
                    artifact_path,
                    artifact_revision,
                    metrics_json,
                    checksum
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    artifact_id,
                    run_id,
                    artifact_type,
                    artifact_name,
                    artifact_url,
                    artifact_path,
                    artifact_revision,
                    metrics_json,
                    checksum,
                ),
            )

    return {
        "id": artifact_id,
        "training_run_id": run_id,
        "artifact_type": artifact_type,
        "artifact_name": artifact_name,
        "artifact_url": artifact_url,
        "artifact_path": artifact_path,
        "artifact_revision": artifact_revision,
        "metrics_json": metrics_json,
        "checksum": checksum,
    }


def latest_training_artifact(run_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text,
                       training_run_id::text,
                       artifact_type,
                       artifact_name,
                       artifact_url,
                       artifact_path,
                       artifact_revision,
                       metrics_json,
                       checksum,
                       created_at::text
                  FROM training_artifacts
                 WHERE training_run_id = %s
              ORDER BY created_at DESC
                 LIMIT 1
                """,
                (run_id,),
            )
            row = cur.fetchone()

    if not row:
        return None

    return {
        "id": row[0],
        "training_run_id": row[1],
        "artifact_type": row[2],
        "artifact_name": row[3],
        "artifact_url": row[4],
        "artifact_path": row[5],
        "artifact_revision": row[6],
        "metrics_json": row[7],
        "checksum": row[8],
        "created_at": row[9],
    }


def latest_training_run() -> dict[str, Any] | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text,
                       status,
                       stage,
                       message,
                       model_version,
                       requested_epochs,
                       requested_batch_size,
                       dataset_size,
                       progress_percent,
                       remote_job_id,
                       remote_provider,
                       remote_status,
                       error_detail,
                       artifact_url,
                       artifact_revision,
                       started_at::text,
                       completed_at::text
                  FROM training_runs
              ORDER BY started_at DESC
                 LIMIT 1
                """
            )
            row = cur.fetchone()

    if not row:
        return None

    return {
        "id": row[0],
        "status": row[1],
        "stage": row[2],
        "message": row[3],
        "model_version": row[4],
        "requested_epochs": row[5],
        "requested_batch_size": row[6],
        "dataset_size": row[7],
        "progress_percent": row[8],
        "remote_job_id": row[9],
        "remote_provider": row[10],
        "remote_status": row[11],
        "error_detail": row[12],
        "artifact_url": row[13],
        "artifact_revision": row[14],
        "started_at": row[15],
        "completed_at": row[16],
    }


def clear_all_data() -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM attendance")
            cur.execute("DELETE FROM images")
            cur.execute("DELETE FROM students")
            cur.execute("DELETE FROM class_days")
            cur.execute("DELETE FROM training_runs")


def set_app_state(key: str, value: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app_state(key, value, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT(key)
                DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                """,
                (key, value),
            )


def get_app_state(key: str, default: str = "") -> str:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM app_state WHERE key = %s", (key,))
            row = cur.fetchone()

    if not row or row[0] is None:
        return default

    return str(row[0])


def set_attendance_lock(locked: bool, reason: str = "") -> None:
    set_app_state("attendance_lock", "true" if locked else "false")
    set_app_state("attendance_lock_reason", reason)


def get_attendance_lock_state() -> dict[str, Any]:
    raw_locked = get_app_state("attendance_lock", "false").strip().lower()
    locked = raw_locked in {"1", "true", "yes", "on"}
    reason = get_app_state("attendance_lock_reason", "").strip()

    return {
        "locked": locked,
        "reason": reason,
    }
