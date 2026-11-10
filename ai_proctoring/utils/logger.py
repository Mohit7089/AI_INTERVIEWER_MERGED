"""Application-wide structured logger, backed by loguru."""
from __future__ import annotations

import os
import sys

from loguru import logger

from config.settings import get_settings

_settings = get_settings()
os.makedirs(_settings.logs_dir, exist_ok=True)

logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {name}:{line} - {message}")
logger.add(
    os.path.join(_settings.logs_dir, "proctoring_service.log"),
    rotation="10 MB",
    retention="14 days",
    level="DEBUG",
    enqueue=True,
)

__all__ = ["logger"]
