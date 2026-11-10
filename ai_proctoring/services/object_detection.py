"""
ObjectDetectionService

Uses YOLOv8 (via `ultralytics`) to flag objects in-frame that are commonly
associated with interview malpractice: mobile phones, books, laptops (a
second device), and additional people (already covered by FaceMesh, but a
"person" detection here reinforces multiple-people signal).

Design choices:
  - Lazy-loaded: the (fairly heavy) ultralytics import and model weights are
    only loaded if `ENABLE_OBJECT_DETECTION=true` and the first detection
    call actually happens. If the package or weights are unavailable, the
    service degrades gracefully (logs a warning, returns no detections)
    instead of crashing the whole pipeline -- object detection is a nice-to
    -have layer on top of the core face/behavior analysis, not a hard
    dependency of it.
  - Run infrequently: YOLO inference is much more expensive than MediaPipe;
    the session manager only calls this every `OBJECT_DETECTION_EVERY_N`
    frames (see config).
"""
from __future__ import annotations

from typing import List, Optional

import numpy as np

from config.settings import get_settings
from models.schemas import DetectedObject
from utils.logger import logger

# CoCo classes we consider "suspicious" in an interview context.
SUSPICIOUS_LABELS = {"cell phone", "book", "laptop", "remote", "tablet"}
CONFIDENCE_THRESHOLD = 0.45


class ObjectDetectionService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._model = None
        self._load_failed = False

    def _ensure_model_loaded(self) -> bool:
        if self._model is not None:
            return True
        if self._load_failed or not self._settings.enable_object_detection:
            return False
        try:
            from ultralytics import YOLO  # heavy import, deferred on purpose

            self._model = YOLO(self._settings.yolo_model_path)
            logger.info(f"YOLOv8 model loaded from {self._settings.yolo_model_path}")
            return True
        except Exception as exc:  # noqa: BLE001 - want to swallow & degrade gracefully
            self._load_failed = True
            logger.warning(
                f"Object detection disabled: could not load YOLOv8 model ({exc}). "
                "Proctoring will continue without object detection."
            )
            return False

    def detect(self, frame_bgr: np.ndarray) -> List[DetectedObject]:
        if not self._settings.enable_object_detection:
            return []
        if not self._ensure_model_loaded():
            return []

        try:
            results = self._model.predict(frame_bgr, verbose=False, conf=CONFIDENCE_THRESHOLD)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"YOLO inference failed for a frame: {exc}")
            return []

        detections: List[DetectedObject] = []
        for result in results:
            names = result.names
            for box in result.boxes:
                cls_id = int(box.cls[0])
                label = names.get(cls_id, str(cls_id))
                if label not in SUSPICIOUS_LABELS:
                    continue
                conf = float(box.conf[0])
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
                detections.append(DetectedObject(label=label, confidence=round(conf, 2),
                                                   bbox=[x1, y1, x2, y2]))
        return detections
