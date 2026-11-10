"""
REST endpoints for session lifecycle management.

Flow used by the frontend:
  1. POST /api/proctoring/sessions/start   -> get session_id + websocket_url
  2. Open the WebSocket, stream frames, receive live analysis + warnings
  3. POST /api/proctoring/sessions/{id}/end -> finalize, persist, generate PDF
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from config.settings import get_settings
from db.repository import ProctorReportRepository
from models.schemas import SessionReport, StartSessionRequest, StartSessionResponse
from services.report_generator import ReportGenerator
from services.session_manager import session_manager
from utils.logger import logger

router = APIRouter(prefix="/api/proctoring/sessions", tags=["proctoring-sessions"])
_settings = get_settings()
_report_generator = ReportGenerator()


@router.post("/start", response_model=StartSessionResponse)
async def start_session(payload: StartSessionRequest) -> StartSessionResponse:
    pipeline = session_manager.create_session(
        interview_id=payload.interview_id, user_id=payload.user_id, candidate_name=payload.candidate_name,
    )
    ws_url = f"/ws/proctoring/{pipeline.session_id}"
    return StartSessionResponse(session_id=pipeline.session_id, websocket_url=ws_url)


@router.post("/{session_id}/end", response_model=SessionReport)
async def end_session(session_id: str) -> SessionReport:
    pipeline = session_manager.end_session(session_id)
    if pipeline is None:
        raise HTTPException(status_code=404, detail="Session not found")

    report = pipeline.build_report()

    try:
        pdf_path = _report_generator.generate(report)
        report.pdf_path = pdf_path
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to generate PDF for session {session_id}: {exc}")

    await ProctorReportRepository.save(report)
    session_manager.remove_session(session_id)
    return report


@router.get("/{session_id}/report", response_model=SessionReport)
async def get_report(session_id: str) -> SessionReport:
    report = await ProctorReportRepository.get_by_session_id(session_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/by-interview/{interview_id}", response_model=SessionReport)
async def get_report_by_interview(interview_id: str) -> SessionReport:
    report = await ProctorReportRepository.get_by_interview_id(interview_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found for this interview")
    return report
