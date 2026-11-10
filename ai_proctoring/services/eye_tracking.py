"""
EyeTrackingService

Implements:
  - Eye Aspect Ratio (EAR) per eye (Soukupova & Cech, 2016 formulation)
  - Iris-based gaze estimation (horizontal/vertical normalized offset of the
    iris centroid relative to the eye corners)
  - Discrete gaze direction classification (center/left/right/up/down/away)
  - A rolling Eye Contact Score (0-100), the percentage of recent frames the
    candidate was looking at the camera.

This is entirely landmark-geometry based (no ML gaze model), which keeps it
fast, explainable, and dependency-light — appropriate for a real-time
proctoring pipeline.
"""
from __future__ import annotations

from collections import deque
from typing import Deque, List, Tuple

from models.schemas import EyeMetrics, GazeDirection
from utils.geometry import (
    LEFT_EYE_EAR,
    RIGHT_EYE_EAR,
    LEFT_IRIS,
    RIGHT_IRIS,
    euclidean_distance,
    polygon_centroid,
)

Point3D = Tuple[float, float, float]


def _eye_aspect_ratio(eye_pts: List[Point3D]) -> float:
    """
    eye_pts ordered as [left_corner, top1, top2, right_corner, bottom2, bottom1]
    EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
    """
    p1, p2, p3, p4, p5, p6 = eye_pts
    vertical_1 = euclidean_distance(p2[:2], p6[:2])
    vertical_2 = euclidean_distance(p3[:2], p5[:2])
    horizontal = euclidean_distance(p1[:2], p4[:2])
    if horizontal == 0:
        return 0.0
    return (vertical_1 + vertical_2) / (2.0 * horizontal)


class EyeTrackingService:
    # Empirically reasonable thresholds for open-eye webcam footage
    EAR_CLOSED_THRESHOLD = 0.18
    GAZE_CENTER_TOLERANCE_X = 0.28
    GAZE_CENTER_TOLERANCE_Y = 0.32

    def __init__(self, eye_contact_window: int = 90) -> None:
        # rolling window of booleans: was the candidate looking at the camera this frame
        self._eye_contact_history: Deque[bool] = deque(maxlen=eye_contact_window)

    def analyze(self, face_landmarks: List[Point3D]) -> EyeMetrics:
        left_eye_pts = [face_landmarks[i] for i in LEFT_EYE_EAR]
        right_eye_pts = [face_landmarks[i] for i in RIGHT_EYE_EAR]

        left_ear = _eye_aspect_ratio(left_eye_pts)
        right_ear = _eye_aspect_ratio(right_eye_pts)
        avg_ear = (left_ear + right_ear) / 2.0

        eyes_closed = avg_ear < self.EAR_CLOSED_THRESHOLD

        gaze_x, gaze_y = self._estimate_gaze_offset(face_landmarks)
        direction = self._classify_direction(gaze_x, gaze_y, eyes_closed)
        looking_at_camera = direction == GazeDirection.CENTER

        self._eye_contact_history.append(looking_at_camera and not eyes_closed)
        eye_contact_score = (
            100.0 * sum(self._eye_contact_history) / len(self._eye_contact_history)
            if self._eye_contact_history
            else 100.0
        )

        return EyeMetrics(
            left_ear=round(left_ear, 4),
            right_ear=round(right_ear, 4),
            avg_ear=round(avg_ear, 4),
            gaze_direction=direction,
            gaze_x=round(gaze_x, 3),
            gaze_y=round(gaze_y, 3),
            is_looking_at_camera=looking_at_camera,
            eye_contact_score=round(eye_contact_score, 1),
        )

    def _estimate_gaze_offset(self, face_landmarks: List[Point3D]) -> Tuple[float, float]:
        """
        Compute the iris centroid's position relative to the eye's bounding
        box for both eyes, normalized to [-1, 1] on each axis, then average
        the two eyes. 0 = perfectly centered (looking at camera).
        """
        offsets = []
        for eye_ear_idx, iris_idx in ((LEFT_EYE_EAR, LEFT_IRIS), (RIGHT_EYE_EAR, RIGHT_IRIS)):
            corner_left = face_landmarks[eye_ear_idx[0]]
            corner_right = face_landmarks[eye_ear_idx[3]]
            top = face_landmarks[eye_ear_idx[1]]
            bottom = face_landmarks[eye_ear_idx[5]]
            iris_pts = [face_landmarks[i] for i in iris_idx]
            iris_center = polygon_centroid(iris_pts)

            eye_width = euclidean_distance(corner_left[:2], corner_right[:2])
            eye_height = euclidean_distance(top[:2], bottom[:2])
            if eye_width == 0 or eye_height == 0:
                continue

            eye_center_x = (corner_left[0] + corner_right[0]) / 2.0
            eye_center_y = (top[1] + bottom[1]) / 2.0

            norm_x = (iris_center[0] - eye_center_x) / (eye_width / 2.0)
            norm_y = (iris_center[1] - eye_center_y) / (eye_height / 2.0)
            offsets.append((norm_x, norm_y))

        if not offsets:
            return 0.0, 0.0

        avg_x = sum(o[0] for o in offsets) / len(offsets)
        avg_y = sum(o[1] for o in offsets) / len(offsets)
        return avg_x, avg_y

    def _classify_direction(self, gaze_x: float, gaze_y: float, eyes_closed: bool) -> GazeDirection:
        if eyes_closed:
            return GazeDirection.AWAY

        if abs(gaze_x) <= self.GAZE_CENTER_TOLERANCE_X and abs(gaze_y) <= self.GAZE_CENTER_TOLERANCE_Y:
            return GazeDirection.CENTER

        # Whichever axis deviates more decides the primary direction label
        if abs(gaze_x) >= abs(gaze_y):
            return GazeDirection.RIGHT if gaze_x > 0 else GazeDirection.LEFT
        return GazeDirection.DOWN if gaze_y > 0 else GazeDirection.UP

    def reset(self) -> None:
        self._eye_contact_history.clear()
