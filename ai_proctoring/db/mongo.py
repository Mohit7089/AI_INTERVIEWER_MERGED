"""
Async MongoDB connection lifecycle, using motor. Connects to the *same*
MongoDB deployment/database as the existing Node/Express backend (see
`server/config/connectDb.js` in the main project) but writes to its own
collections (`proctor_sessions`, `proctor_reports`), so the two backends
never contend over the same documents.
"""
from __future__ import annotations

from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from config.settings import get_settings
from utils.logger import logger

_settings = get_settings()

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def connect_to_mongo() -> None:
    global _client, _db
    try:
        _client = AsyncIOMotorClient(_settings.mongo_uri, serverSelectionTimeoutMS=5000)
        await _client.admin.command("ping")
        _db = _client[_settings.mongo_db_name]
        logger.info(f"Connected to MongoDB database '{_settings.mongo_db_name}'")
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            f"Could not connect to MongoDB ({exc}). The service will still run; "
            "session persistence will be unavailable until MongoDB is reachable."
        )
        _client = None
        _db = None


async def close_mongo_connection() -> None:
    if _client is not None:
        _client.close()
        logger.info("MongoDB connection closed")


def get_database() -> Optional[AsyncIOMotorDatabase]:
    return _db
