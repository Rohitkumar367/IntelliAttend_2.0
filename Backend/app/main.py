from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool

from app.api.admin import router as admin_router
from app.api.attendance import router as attendance_router
from app.api.students import router as students_router
from app.api.training import router as training_router
from app.core.config import settings
from app.db.session import init_db
from app.services.embedding_service import ensure_embeddings_loaded


# print("DB URL LOADED:", settings.supabase_db_url)

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App
app = FastAPI(title=settings.app_name, version=settings.app_version)

# CORS
allow_origins = [
    x.strip() for x in settings.cors_allow_origins.split(",") if x.strip()
]

if not allow_origins:
    logger.warning("No CORS origins set, defaulting to '*'")
    allow_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup
@app.on_event("startup")
async def startup() -> None:
    logger.info("🚀 Starting application...")

    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as exc:
        logger.error(f"Database init failed: {exc}")

    try:
        await run_in_threadpool(ensure_embeddings_loaded)
        logger.info("Model loaded successfully")
    except Exception as exc:
        logger.error(f"Model loading failed: {exc}")


# Routes
@app.get("/")
def root() -> dict:
    return {"message": f"{settings.app_name} is running."}

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name}

# Routers
app.include_router(students_router)
app.include_router(training_router)
app.include_router(attendance_router)
app.include_router(admin_router)
