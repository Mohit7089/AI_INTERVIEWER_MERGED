"""
ProctorReportRepository: persistence for finalized session reports.

Wrapped so callers never touch raw Mongo collections directly, and so the
service degrades gracefully (returns None / no-ops with a logged warning)
if MongoDB is unreachable rather than crashing report generation.
"""
from __future__ import annotations

from typing import List, Optional

from db.mongo import get_database
from models.db_models import (
    PROCTOR_REPORTS_COLLECTION,
    document_to_session_report,
    session_report_to_document,
)
from models.schemas import SessionReport
from utils.logger import logger


class ProctorReportRepository:
    @staticmethod
    async def save(report: SessionReport) -> bool:
        db = get_database()
        if db is None:
            logger.warning("MongoDB unavailable — report was generated but not persisted.")
            return False
        doc = session_report_to_document(report)
        await db[PROCTOR_REPORTS_COLLECTION].replace_one({"_id": report.session_id}, doc, upsert=True)
        return True

    @staticmethod
    async def get_by_session_id(session_id: str) -> Optional[SessionReport]:
        db = get_database()
        if db is None:
            return None
        doc = await db[PROCTOR_REPORTS_COLLECTION].find_one({"_id": session_id})
        return document_to_session_report(doc) if doc else None

    @staticmethod
    async def get_by_interview_id(interview_id: str) -> Optional[SessionReport]:
        db = get_database()
        if db is None:
            return None
        doc = await db[PROCTOR_REPORTS_COLLECTION].find_one(
            {"interview_id": interview_id}, sort=[("ended_at", -1)]
        )
        return document_to_session_report(doc) if doc else None

    @staticmethod
    async def list_by_user(user_id: str, limit: int = 20) -> List[SessionReport]:
        db = get_database()
        if db is None:
            return []
        cursor = db[PROCTOR_REPORTS_COLLECTION].find({"user_id": user_id}).sort(
            "ended_at", -1
        ).limit(limit)
        return [document_to_session_report(doc) async for doc in cursor]
