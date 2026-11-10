"""
MongoDB document (de)serialization helpers.

We deliberately avoid an ODM (Beanie/MongoEngine) here to keep the service
lightweight and dependency-thin, using `motor` directly with Pydantic models
as the single source of truth for shape. These helpers convert between
Pydantic models and plain dicts suitable for Mongo documents.
"""
from __future__ import annotations

from typing import Any, Dict

from models.schemas import FrameAnalysisResult, SessionReport

PROCTOR_SESSIONS_COLLECTION = "proctor_sessions"
PROCTOR_FRAMES_COLLECTION = "proctor_frames"
PROCTOR_REPORTS_COLLECTION = "proctor_reports"


def session_report_to_document(report: SessionReport) -> Dict[str, Any]:
    """Convert a SessionReport into a Mongo-storable dict (datetimes kept as-is; motor handles them)."""
    doc = report.model_dump(mode="python")
    doc["_id"] = report.session_id
    return doc


def frame_result_to_document(result: FrameAnalysisResult) -> Dict[str, Any]:
    doc = result.model_dump(mode="python")
    return doc


def document_to_session_report(doc: Dict[str, Any]) -> SessionReport:
    doc = dict(doc)
    doc.pop("_id", None)
    return SessionReport(**doc)
