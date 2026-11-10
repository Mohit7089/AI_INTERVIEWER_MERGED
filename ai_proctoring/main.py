"""
AI Interview Proctoring & Behavioral Analysis Service
------------------------------------------------------
Entry point. Run with:

    uvicorn main:app --host 0.0.0.0 --port 8001 --reload

Architecture (per request):

    Webcam -> OpenCV Capture -> MediaPipe FaceMesh + Pose -> Feature
    Extraction -> Behavior Analysis -> Proctoring Engine -> Report Generator

The FastAPI app exposes:
  - REST endpoints under /api/proctoring/... for session lifecycle and reports
  - A WebSocket endpoint at /ws/proctoring/{session_id} for real-time frame streaming
  - /health for liveness checks
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes_report import router as report_router
from api.routes_session import router as session_router
from api.ws_stream import router as ws_router
from config.settings import get_settings
from db.mongo import close_mongo_connection, connect_to_mongo
from utils.logger import logger

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Interview Proctoring Service...")
    await connect_to_mongo()
    yield
    await close_mongo_connection()
    logger.info("Proctoring service shut down cleanly.")


app = FastAPI(
    title="AI Interview Proctoring & Behavioral Analysis Service",
    description=(
        "Real-time webcam-based proctoring and behavioral analytics for the "
        "AI Interviewer platform: face/eye/head-pose tracking, blink and "
        "posture analysis, reading detection, explainable behavior scoring, "
        "proctoring violation detection, and PDF report generation."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session_router)
app.include_router(report_router)
app.include_router(ws_router)


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    return {"status": "ok", "service": "ai-interview-proctoring"}
