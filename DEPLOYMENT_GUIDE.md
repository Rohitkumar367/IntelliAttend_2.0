# Free Deployment Guide

## Stack

- Frontend: Vercel
- Backend: Render (FastAPI)
- Images: Cloudinary
- Database: Supabase PostgreSQL
- Model artifacts: Hugging Face model repo (trained model outputs)

## 1) Frontend deployment (Vercel)

- Connect repository and set project root to `Frontend`
- Build command: `npm run build`
- Output directory: `dist`
- Environment variable: `VITE_API_BASE=<your-render-backend-url>`

## 2) Backend deployment (Render)

- Create Web Service from `Backend`
- Runtime: Python
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Add environment variables from `Backend/.env.example`

Required HF-related env vars:
- `HF_TOKEN`
- `HF_MODEL_REPO_ID`
- `HF_SPACE_ID`
- `HF_SPACE_API_URL`
- `HF_SPACE_TRAIN_PATH`
- `HF_SPACE_STATUS_PATH_TEMPLATE`
- `HF_PRIVATE_REPO`

## 3) Supabase PostgreSQL setup

Create tables (or allow backend auto-init on first run):
- `students`
- `images`
- `attendance`
- `class_days`
- `training_runs`
- `training_artifacts`
- `app_state`

Use the Postgres connection string as `SUPABASE_DB_URL`.

## 4) Cloudinary setup

Create account and set:
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`
- `CLOUDINARY_FOLDER=face_attendance`

Each student's uploaded images are stored in Cloudinary and tracked in DB using:
- `public_id`
- `url`

Backend stores up to 40 selected images per student (out of 50 captured).

## 5) Training (remote HF)

- Training is executed in a Hugging Face Space (VGGFace label in UI/logs)
- Trained model artifacts are uploaded to Hugging Face model repo
- Training status available via `GET /training/status`
- If HF is rate-limited, training may complete with a warning message about artifact upload

## 6) Attendance lock behavior

- When student data changes (add/delete/reset), attendance marking is locked
- `/attendance/recognize` returns `attendance_enabled: false` until training completes
- Lock is cleared automatically after training completion

## 7) Core flows

### Add student
- Upload ~50 images from frontend
- Backend stores selected images in Cloudinary (up to 40)
- Backend stores image references in Supabase
- Attendance marking becomes locked until training completes

### Train model
- Backend launches HF Space training job
- Training artifacts are saved to Hugging Face model repo
- Attendance marking is unlocked after training completion

### Attendance
- Frontend captures webcam frames and posts to `/attendance/recognize`
- Backend runs recognition and logs attendance in Supabase (when attendance is enabled)

### Delete student
- Deletes student images from Cloudinary
- Removes student/image/attendance DB rows
- Attendance marking becomes locked until training completes

### Reset system
- Deletes Cloudinary images under folder
- Clears DB tables
- Resets attendance lock state

## 8) Notes

- Render free tier can sleep; first request after idle may be slow.
- HF rate limits can delay or skip artifact upload; training completion may include a warning message.
