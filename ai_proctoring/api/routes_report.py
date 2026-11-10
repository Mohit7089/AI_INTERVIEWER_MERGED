"""REST endpoints for retrieving generated PDF reports and report history."""
from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from db.repository import ProctorReportRepository
from models.schemas import SessionReport

router = APIRouter(prefix="/api/proctoring/reports", tags=["proctoring-reports"])


@router.get("/{session_id}/pdf")
async def download_pdf(session_id: str):
    report = await ProctorReportRepository.get_by_session_id(session_id)
    if report is None or not report.pdf_path or not os.path.exists(report.pdf_path):
        raise HTTPException(status_code=404, detail="PDF report not found")
    return FileResponse(
        report.pdf_path, media_type="application/pdf",
        filename=f"interview_report_{session_id}.pdf",
    )


@router.get("/user/{user_id}", response_model=list[SessionReport])
async def list_user_reports(user_id: str, limit: int = 20):
    return await ProctorReportRepository.list_by_user(user_id, limit=limit)
