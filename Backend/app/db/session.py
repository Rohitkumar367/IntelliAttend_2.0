from contextlib import contextmanager
from typing import Iterator

import psycopg

from app.core.config import settings


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    if not settings.supabase_db_url:
        raise RuntimeError("SUPABASE_DB_URL is not configured")

    conn = psycopg.connect(settings.supabase_db_url)
    # Supabase/pgBouncer transaction pooling can reuse backend sessions across
    # client connections, which breaks psycopg's auto-prepared statement names.
    # Disable automatic prepares to avoid DuplicatePreparedStatement errors.
    conn.prepare_threshold = None
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS students (
                    id UUID PRIMARY KEY,
                    name TEXT NOT NULL,
                    roll_no TEXT UNIQUE,
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS images (
                    id UUID PRIMARY KEY,
                    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                    public_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS attendance (
                    id UUID PRIMARY KEY,
                    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                    attended_on DATE NOT NULL,
                    attended_at TIME NOT NULL,
                    confidence DOUBLE PRECISION,
                    source TEXT NOT NULL DEFAULT 'webcam',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(student_id, attended_on)
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS class_days (
                    day DATE PRIMARY KEY,
                    is_class_day BOOLEAN NOT NULL DEFAULT TRUE
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS training_runs (
                    id UUID PRIMARY KEY,
                    status TEXT NOT NULL,
                    stage TEXT,
                    message TEXT,
                    model_version TEXT,
                    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    completed_at TIMESTAMPTZ
                )
                """
            )

            # Backward-compatible schema upgrades for real remote training tracking
            cur.execute("ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS requested_epochs INTEGER")
            cur.execute("ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS requested_batch_size INTEGER")
            cur.execute("ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS dataset_size INTEGER")
            cur.execute("ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS progress_percent DOUBLE PRECISION DEFAULT 0")
            cur.execute("ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS remote_job_id TEXT")
            cur.execute("ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS remote_provider TEXT")
            cur.execute("ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS remote_status TEXT")
            cur.execute("ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS error_detail TEXT")
            cur.execute("ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS artifact_url TEXT")
            cur.execute("ALTER TABLE training_runs ADD COLUMN IF NOT EXISTS artifact_revision TEXT")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS training_artifacts (
                    id UUID PRIMARY KEY,
                    training_run_id UUID NOT NULL REFERENCES training_runs(id) ON DELETE CASCADE,
                    artifact_type TEXT NOT NULL,
                    artifact_name TEXT NOT NULL,
                    artifact_url TEXT NOT NULL,
                    artifact_path TEXT,
                    artifact_revision TEXT,
                    metrics_json TEXT,
                    checksum TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS app_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )

            cur.execute(
                """
                INSERT INTO app_state(key, value)
                VALUES ('attendance_lock', 'false')
                ON CONFLICT(key) DO NOTHING
                """
            )

            cur.execute(
                """
                INSERT INTO app_state(key, value)
                VALUES ('attendance_lock_reason', '')
                ON CONFLICT(key) DO NOTHING
                """
            )
