"""
FaceMeshService: thin, stateful wrapper around MediaPipe FaceMesh.

Responsibilities:
  - Run FaceMesh (478 landmarks, iris refinement enabled) on a BGR frame.
  - Convert normalized landmarks to pixel-space coordinates.
  - Compute FaceQuality (face count, visibility, brightness, size-in-frame).

This module owns exactly one concern: "where is the face and its landmarks,
and is the image of it usable" — all higher-level interpretation (gaze,
blinks, etc.) lives in dedicated services that consume this output.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import cv2
import mediapipe as mp
import numpy as np

from models.schemas import FaceQuality
from utils.geometry import FACE_OVAL, bounding_box, landmarks_to_pixel_coords


@dataclass
class FaceMeshOutput:
    faces_pixel_landmarks: List[List[tuple]]  # one list of (x,y,z) per detected face
    quality: FaceQuality


class FaceMeshService:
    def __init__(self, max_num_faces: int = 3, min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5) -> None:
        self._mp_face_mesh = mp.solutions.face_mesh
        self._face_mesh = self._mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=max_num_faces,
            refine_landmarks=True,  # required for iris landmarks (468-477)
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def process(self, frame_bgr: np.ndarray) -> FaceMeshOutput:
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self._face_mesh.process(rgb)

        faces: List[List[tuple]] = []
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                faces.append(landmarks_to_pixel_coords(face_landmarks.landmark, w, h))

        quality = self._assess_quality(frame_bgr, faces, w, h)
        return FaceMeshOutput(faces_pixel_landmarks=faces, quality=quality)

    @staticmethod
    def _assess_quality(frame_bgr: np.ndarray, faces: List[List[tuple]], w: int, h: int) -> FaceQuality:
        faces_detected = len(faces)
        if faces_detected == 0:
            return FaceQuality(faces_detected=0, face_visible=False, brightness_ok=True,
                                face_size_ratio=0.0, quality_score=0.0)

        # Use the largest face for quality assessment (primary candidate)
        primary = max(faces, key=lambda pts: FaceMeshService._face_area(pts, w, h))
        oval_pts = [primary[i] for i in FACE_OVAL]
        x_min, y_min, x_max, y_max = bounding_box(oval_pts)
        face_area = max(0.0, (x_max - x_min)) * max(0.0, (y_max - y_min))
        frame_area = float(w * h)
        size_ratio = face_area / frame_area if frame_area else 0.0

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        x0, y0 = max(int(x_min), 0), max(int(y_min), 0)
        x1, y1 = min(int(x_max), w), min(int(y_max), h)
        roi = gray[y0:y1, x0:x1]
        brightness = float(np.mean(roi)) if roi.size else 0.0
        brightness_ok = 40.0 <= brightness <= 230.0

        # Quality score: combination of size-in-frame and brightness, penalized for extremes
        size_score = 100.0 if 0.03 <= size_ratio <= 0.55 else max(0.0, 100.0 - abs(size_ratio - 0.2) * 200)
        brightness_score = 100.0 if brightness_ok else max(0.0, 100.0 - abs(brightness - 135.0))
        quality_score = float(np.clip(0.6 * size_score + 0.4 * brightness_score, 0.0, 100.0))

        return FaceQuality(
            faces_detected=faces_detected,
            face_visible=size_ratio > 0.01,
            brightness_ok=brightness_ok,
            face_size_ratio=round(size_ratio, 4),
            quality_score=round(quality_score, 1),
        )

    @staticmethod
    def _face_area(pts: List[tuple], w: int, h: int) -> float:
        oval_pts = [pts[i] for i in FACE_OVAL]
        x_min, y_min, x_max, y_max = bounding_box(oval_pts)
        return max(0.0, (x_max - x_min)) * max(0.0, (y_max - y_min))

    def close(self) -> None:
        self._face_mesh.close()
