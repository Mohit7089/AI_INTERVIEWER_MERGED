"""
WebSocket endpoint: `/ws/proctoring/{session_id}`

Protocol (JSON messages both ways):

Client -> Server:
  {"type": "frame", "image": "data:image/jpeg;base64,...", "frame_index": 42}
  {"type": "event", "event": "fullscreen_exit"}

Server -> Client:
  {"type": "analysis", "result": <FrameAnalysisResult>}   -- sent for every processed frame
  {"type": "warning",  "warning": <WarningEvent>}         -- sent immediately for each new confirmed warning
  {"type": "error", "message": "..."}                     -- malformed payload / decode failure

Frame throttling: to keep the pipeline real-time under load, only every
Nth incoming frame is actually run through the CV pipeline
(`FRAME_PROCESS_EVERY_N`); others are acknowledged but skipped. This keeps
server CPU bounded even if the browser sends frames faster than the
pipeline can process them.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config.settings import get_settings
from models.schemas import ClientEventMessage
from services.session_manager import session_manager
from utils.image_utils import base64_to_frame
from utils.logger import logger

router = APIRouter()
_settings = get_settings()


@router.websocket("/ws/proctoring/{session_id}")
async def proctoring_stream(websocket: WebSocket, session_id: str) -> None:
    pipeline = session_manager.get_session(session_id)
    if pipeline is None:
        await websocket.close(code=4404, reason="Session not found. Call /start first.")
        return

    await websocket.accept()
    logger.info(f"WebSocket connected for session {session_id}")
    raw_frame_counter = 0

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON payload"})
                continue

            msg_type = payload.get("type")

            if msg_type == "event":
                event = ClientEventMessage(**payload)
                pipeline.handle_client_event(event)
                continue

            if msg_type != "frame":
                await websocket.send_json({"type": "error", "message": f"Unknown message type '{msg_type}'"})
                continue

            raw_frame_counter += 1
            if raw_frame_counter % _settings.frame_process_every_n != 0:
                continue  # throttle: skip pipeline processing for this frame

            image_data = payload.get("image")
            if not image_data:
                await websocket.send_json({"type": "error", "message": "Missing 'image' field"})
                continue

            frame = base64_to_frame(image_data)
            if frame is None:
                await websocket.send_json({"type": "error", "message": "Could not decode image"})
                continue

            result = pipeline.process_frame(frame)

            await websocket.send_json({"type": "analysis", "result": json.loads(result.model_dump_json())})
            for warning in result.warnings:
                await websocket.send_json({"type": "warning", "warning": json.loads(warning.model_dump_json())})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Unexpected error in proctoring stream for session {session_id}: {exc}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except Exception:  # noqa: BLE001
            pass
