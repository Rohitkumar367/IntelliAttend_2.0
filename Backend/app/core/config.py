from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True,
    )

    # ------------------ App Info ------------------
    app_name: str = "Face Recognition Attendance API"
    app_version: str = "2.0.0"
    env: str = "development"
    log_level: str = "INFO"

    # ------------------ Paths ------------------
    backend_root: Path = Path(__file__).resolve().parents[2]
    local_models_root: Path = backend_root / "models"
    embeddings_path: Path = local_models_root / "models.npz"

    # ------------------ CORS ------------------
    cors_allow_origins: str = "http://localhost:5173"

    # ------------------ Database ------------------
    supabase_db_url: str = ""

    @field_validator("supabase_db_url")
    def validate_db_url(cls, v):
        if not v:
            raise ValueError("SUPABASE_DB_URL is required")
        return v

    # ------------------ Cloudinary ------------------
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    cloudinary_folder: str = "face_attendance"

    # ------------------ Security ------------------
    reset_confirm_token: str = "RESET_SEMESTER"

    # ------------------ ML Config ------------------
    embedding_threshold: float = 0.65

    # ------------------ Remote Training (Hugging Face) ------------------
    hf_token: str = ""
    hf_model_repo_id: str = ""
    hf_space_id: str = ""
    hf_space_api_url: str = ""
    hf_callback_secret: str = ""
    hf_poll_interval_seconds: int = 8
    hf_training_timeout_seconds: int = 5400
    hf_artifact_subdir: str = "training_artifacts"
    hf_private_repo: bool = True
    hf_org_name: str = ""
    hf_dataset_repo_id: str = ""
    hf_space_train_path: str = "/api/train"
    hf_space_status_path_template: str = "/api/train/status/{job_id}"
    hf_embeddings_artifact_path: str = "models/models.npz"
    hf_embeddings_ref: str = "main"

    @field_validator("embedding_threshold")
    def validate_threshold(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("embedding_threshold must be between 0 and 1")
        return v

    @field_validator("hf_poll_interval_seconds", "hf_training_timeout_seconds")
    def validate_positive_seconds(cls, v):
        if v <= 0:
            raise ValueError("Polling and timeout values must be > 0")
        return v

    @field_validator("hf_embeddings_artifact_path")
    def validate_hf_embeddings_artifact_path(cls, v):
        cleaned = v.strip().replace("\\", "/")
        if not cleaned:
            raise ValueError("hf_embeddings_artifact_path cannot be empty")
        return cleaned


settings = Settings()