# IntelliAttend 2.0

Face attendance system with a FastAPI backend and a React (Vite) frontend. It supports student management, face-based attendance recognition, and remote model training via Hugging Face Spaces.

## Features

- Student management with image storage (Cloudinary)
- Face-based attendance recognition and logging (Supabase PostgreSQL)
- Remote training orchestration (Hugging Face Space)
- Monthly attendance summaries with backward-month logic
- Admin tools for resets and embeddings rebuilds

## Repo Structure

- Backend/ - FastAPI service, training orchestration, embeddings
- Frontend/ - React control panel (Vite)
- DEPLOYMENT_GUIDE.md - deployment steps
- FULL_PROJECT_PROMPT.md - project spec and prompt context

## Quick Start

### 1) Backend

From Backend/:

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Copy and configure environment variables:

```bash
copy .env.example .env
```

See Backend/README.md for the full list of required environment variables and API notes.

### 2) Frontend

From Frontend/:

```bash
npm install
npm run dev
```

Set API base URL in Frontend/.env:

```bash
VITE_API_BASE=http://localhost:8000
```

See Frontend/README.md for UI notes and feature behavior.

## Configuration Notes

- Backend environment variables live in Backend/.env (copied from Backend/.env.example).
- Frontend environment variables live in Frontend/.env.
- Embeddings are stored in Backend/models/models.npz.

## Local Development URLs

- Backend API: http://127.0.0.1:8000
- Frontend UI: http://localhost:5173

## Documentation

- DEPLOYMENT_GUIDE.md
- Backend/README.md
- Frontend/README.md

