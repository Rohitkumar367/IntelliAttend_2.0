# Backend (FastAPI)

Backend service for the Face Attendance project.

It provides:
- student management with Cloudinary image storage
- attendance recognition and attendance logs in Supabase PostgreSQL
- remote model training orchestration through Hugging Face Space
- embeddings rebuild/sync for attendance recognition

## Quick Start

1. Copy `.env.example` to `.env`.
2. Fill all required credentials.
3. Create and activate virtual environment.
4. Install dependencies.
5. Run the API server.

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Environment Variables

Use `.env.example` as the source of truth.

Core required:
- `SUPABASE_DB_URL`
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`
- `CLOUDINARY_FOLDER`
- `CORS_ALLOW_ORIGINS`
- `RESET_CONFIRM_TOKEN`
- `EMBEDDING_THRESHOLD`
- `APP_NAME`
- `APP_VERSION`
- `ENV`
- `LOG_LEVEL`

Required for remote training:
- `HF_TOKEN`
- `HF_MODEL_REPO_ID`
- `HF_SPACE_ID`
- `HF_SPACE_API_URL`
- `HF_CALLBACK_SECRET`
- `HF_POLL_INTERVAL_SECONDS`
- `HF_TRAINING_TIMEOUT_SECONDS`
- `HF_ARTIFACT_SUBDIR`
- `HF_PRIVATE_REPO`
- `HF_EMBEDDINGS_ARTIFACT_PATH`
- `HF_EMBEDDINGS_REF`
- `HF_SPACE_TRAIN_PATH`
- `HF_SPACE_STATUS_PATH_TEMPLATE`

Optional remote training fields:
- `HF_ORG_NAME`
- `HF_DATASET_REPO_ID`

## Hugging Face Trainer Space

- Trainer app source: `hf_space_trainer/app.py`
- Trainer dependencies: `hf_space_trainer/requirements.txt`
- Required trainer routes:
	- `POST /api/train`
	- `GET /api/train/status/{job_id}`

## API Endpoints

- `GET /` - service info
- `GET /health` - basic health response
- `GET /students` - list students
- `POST /students` - add student with images (multipart: `name`, optional `roll_no`, `images[]`)
- `DELETE /students/{student_id}` - delete by student id
- `DELETE /students/by-roll/{roll_no}` - delete by roll number
- `POST /training/start` - start remote training
- `GET /training/status` - latest training status
- `POST /attendance/import` - bulk attendance import (json `items[]`)
- `POST /attendance/recognize` - recognize and mark attendance from uploaded image
- `POST /attendance/class-day` - set class day flag
- `GET /attendance/monthly-summary` - aggregated report using backward-month logic
- `DELETE /admin/reset-semester` - reset semester data (requires `x-confirm-token` header)
- `POST /admin/rebuild-embeddings` - manually rebuild embeddings

## Important Behavior Notes

### 1) Monthly summary semantics

`GET /attendance/monthly-summary?year=YYYY&month=N`

- `month` is treated as months count, not calendar month number.
- It starts from current month and moves backward.
- Example in April: `month=4` means April + March + February + January.

### 2) Training constraints

`POST /training/start` accepts:
- `epochs`: `25`
- `batch_size`: `4`, `8`, or `16`

### 3) Recognition pipeline

- Attendance recognition uses embeddings (`models/models.npz`), not the remote VGGFace model label.
- Remote training updates model artifacts and then triggers embeddings refresh for attendance flow.

### 4) Embeddings persistence

- Local embeddings path: `models/models.npz`
- After rebuild, embeddings are uploaded to Hugging Face model repo (`HF_EMBEDDINGS_ARTIFACT_PATH`).
- On startup, backend tries to download embeddings first; if unavailable, it rebuilds.

## Minimal Request Examples

Training start:

```bash
curl -X POST http://127.0.0.1:8000/training/start \
	-H "Content-Type: application/json" \
	-d '{"epochs": 25, "batch_size": 8}'
```

Monthly summary (last 4 months from current month):

```bash
curl "http://127.0.0.1:8000/attendance/monthly-summary?year=2026&month=4"
```
