"""
Image codec helpers: base64 <-> numpy BGR frames, and resizing.

The frontend streams JPEG frames as base64 data-URLs over the WebSocket
(`data:image/jpeg;base64,<...>`). These helpers decode that payload into an
OpenCV-compatible numpy array and back.
"""
from __future__ import annotations

import base64
import re
from typing import Optional

import cv2
import numpy as np

_DATA_URL_RE = re.compile(r"^data:image/\w+;base64,")


def base64_to_frame(data_url: str) -> Optional[np.ndarray]:
    """Decode a base64 (optionally data-URL prefixed) JPEG/PNG string into a BGR numpy frame."""
    try:
        raw = _DATA_URL_RE.sub("", data_url)
        img_bytes = base64.b64decode(raw)
        np_arr = np.frombuffer(img_bytes, dtype=np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return frame
    except Exception:
        return None


def frame_to_base64(frame: np.ndarray, quality: int = 80) -> str:
    """Encode a BGR numpy frame back into a base64 JPEG data-URL (used for annotated previews)."""
    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        return ""
    b64 = base64.b64encode(buf).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def resize_frame(frame: np.ndarray, max_width: int) -> np.ndarray:
    """Downscale a frame so its width does not exceed `max_width`, preserving aspect ratio."""
    h, w = frame.shape[:2]
    if w <= max_width:
        return frame
    scale = max_width / float(w)
    return cv2.resize(frame, (max_width, int(h * scale)), interpolation=cv2.INTER_AREA)
