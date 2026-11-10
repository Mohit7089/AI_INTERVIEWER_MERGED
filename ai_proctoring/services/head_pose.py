"""
HeadPoseService: 3D head pose (pitch, yaw, roll) via OpenCV's solvePnP,
using a canonical 3D face model matched against 6 stable 2D landmarks.

Also tracks a rolling Head Stability Score: how much the head pose angles
vary over a short window (high variance -> low stability -> likely fidgeting,
distraction, or someone repeatedly checking a second screen/notes).
"""
from __future__ import annotations

import math
from collections import deque
from typing import Deque, List, Tuple

import cv2
import numpy as np

from models.schemas import HeadPoseMetrics
from utils.geometry import HEAD_POSE_LANDMARKS

Point3D = Tuple[float, float, float]

# Canonical 3D face model points (arbitrary units, roughly millimeters),
# in the same order as HEAD_POSE_LANDMARKS. This is the standard model used
# widely for solvePnP-based head pose estimation.
_MODEL_POINTS_3D = np.array([
    (0.0, 0.0, 0.0),          # nose_tip
    (0.0, -63.6, -12.5),      # chin
    (-43.3, 32.7, -26.0),     # left_eye_left_corner
    (43.3, 32.7, -26.0),      # right_eye_right_corner
    (-28.9, -28.9, -24.1),    # mouth_left_corner
    (28.9, -28.9, -24.1),     # mouth_right_corner
], dtype=np.float64)


class HeadPoseService:
    def __init__(self, frame_width: int, frame_height: int, stability_window: int = 30) -> None:
        self.frame_width = frame_width
        self.frame_height = frame_height
        self._camera_matrix = self._build_camera_matrix(frame_width, frame_height)
        self._dist_coeffs = np.zeros((4, 1))  # assume no lens distortion
        self._history: Deque[Tuple[float, float, float]] = deque(maxlen=stability_window)

    @staticmethod
    def _build_camera_matrix(w: int, h: int) -> np.ndarray:
        focal_length = w  # reasonable approximation for a webcam
        center = (w / 2.0, h / 2.0)
        return np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1],
        ], dtype=np.float64)

    def analyze(self, face_landmarks: List[Point3D]) -> HeadPoseMetrics:
        image_points = np.array([
            face_landmarks[HEAD_POSE_LANDMARKS["nose_tip"]][:2],
            face_landmarks[HEAD_POSE_LANDMARKS["chin"]][:2],
            face_landmarks[HEAD_POSE_LANDMARKS["left_eye_left_corner"]][:2],
            face_landmarks[HEAD_POSE_LANDMARKS["right_eye_right_corner"]][:2],
            face_landmarks[HEAD_POSE_LANDMARKS["mouth_left_corner"]][:2],
            face_landmarks[HEAD_POSE_LANDMARKS["mouth_right_corner"]][:2],
        ], dtype=np.float64)

        success, rotation_vec, _translation_vec = cv2.solvePnP(
            _MODEL_POINTS_3D, image_points, self._camera_matrix, self._dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )

        if not success:
            return HeadPoseMetrics(pitch=0.0, yaw=0.0, roll=0.0, stability_score=100.0)

        rotation_matrix, _ = cv2.Rodrigues(rotation_vec)
        pitch, yaw, roll = self._rotation_matrix_to_euler(rotation_matrix)

        self._history.append((pitch, yaw, roll))
        stability_score = self._compute_stability_score()

        return HeadPoseMetrics(
            pitch=round(pitch, 2),
            yaw=round(yaw, 2),
            roll=round(roll, 2),
            stability_score=round(stability_score, 1),
        )

    @staticmethod
    def _rotation_matrix_to_euler(r: np.ndarray) -> Tuple[float, float, float]:
        """Convert a rotation matrix to (pitch, yaw, roll) in degrees."""
        sy = math.sqrt(r[0, 0] ** 2 + r[1, 0] ** 2)
        singular = sy < 1e-6

        if not singular:
            pitch = math.atan2(-r[2, 0], sy)
            yaw = math.atan2(r[1, 0], r[0, 0])
            roll = math.atan2(r[2, 1], r[2, 2])
        else:
            pitch = math.atan2(-r[2, 0], sy)
            yaw = 0.0
            roll = math.atan2(-r[1, 2], r[1, 1])

        return math.degrees(pitch), math.degrees(yaw), math.degrees(roll)

    def _compute_stability_score(self) -> float:
        if len(self._history) < 2:
            return 100.0
        arr = np.array(self._history)
        # standard deviation across the window for each angle, summed
        variability = float(np.sum(np.std(arr, axis=0)))
        # Empirically, total std under ~3 degrees = very stable, over ~25 = very unstable
        score = 100.0 - min(100.0, (variability / 25.0) * 100.0)
        return max(0.0, score)

    def reset(self) -> None:
        self._history.clear()
