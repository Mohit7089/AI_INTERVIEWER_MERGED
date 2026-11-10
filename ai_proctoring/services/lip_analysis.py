"""
LipAnalysisService

Landmark-geometry based mouth analysis:
  - Mouth Opening Ratio: vertical lip gap normalized by face width.
  - Speaking detection: short-term temporal variance of the mouth opening
    ratio (a still, closed mouth = silence; oscillating opening = speech).
  - Lip Compression: how tightly the lips are pressed together relative to
    their resting/open state (a nervousness/tension indicator).
  - Smile detection: mouth-corner width relative to a neutral baseline plus
    a slight upward corner lift.
"""
from __future__ import annotations

from collections import deque
from typing import Deque, List, Tuple

from models.schemas import LipMetrics
from utils.geometry import (
    MOUTH_LEFT_CORNER,
    MOUTH_RIGHT_CORNER,
    UPPER_LIP_OUTER,
    LOWER_LIP_OUTER,
    UPPER_LIP_TOP,
    LOWER_LIP_BOTTOM,
    LEFT_EYE_EAR,
    RIGHT_EYE_EAR,
    euclidean_distance,
)

Point3D = Tuple[float, float, float]


class LipAnalysisService:
    def __init__(self, speaking_window: int = 8, speaking_variance_threshold: float = 0.0009) -> None:
        self._mouth_ratio_history: Deque[float] = deque(maxlen=speaking_window)
        self.speaking_variance_threshold = speaking_variance_threshold

    def analyze(self, face_landmarks: List[Point3D]) -> LipMetrics:
        upper = face_landmarks[UPPER_LIP_TOP]
        lower = face_landmarks[LOWER_LIP_BOTTOM]
        outer_upper = face_landmarks[UPPER_LIP_OUTER]
        outer_lower = face_landmarks[LOWER_LIP_OUTER]
        left_corner = face_landmarks[MOUTH_LEFT_CORNER]
        right_corner = face_landmarks[MOUTH_RIGHT_CORNER]

        # Normalize by face width (distance between outer eye corners) so the
        # ratio is roughly scale/distance-invariant.
        face_width = euclidean_distance(
            face_landmarks[LEFT_EYE_EAR[0]][:2], face_landmarks[RIGHT_EYE_EAR[3]][:2]
        )
        face_width = face_width if face_width > 1e-3 else 1.0

        mouth_gap = euclidean_distance(upper[:2], lower[:2])
        mouth_open_ratio = mouth_gap / face_width

        outer_gap = euclidean_distance(outer_upper[:2], outer_lower[:2])
        lip_compression = max(0.0, 1.0 - (outer_gap / face_width) / 0.12)  # heuristic normalization
        lip_compression = min(1.0, lip_compression)

        mouth_width = euclidean_distance(left_corner[:2], right_corner[:2])
        mouth_width_ratio = mouth_width / face_width

        self._mouth_ratio_history.append(mouth_open_ratio)
        is_speaking = self._detect_speaking()

        # Smile heuristic: corners pulled wide relative to typical neutral ratio (~0.45-0.5)
        # combined with a small mouth opening (distinguishes smile from talking/surprise).
        is_smiling = mouth_width_ratio > 0.52 and mouth_open_ratio < 0.06

        return LipMetrics(
            is_speaking=is_speaking,
            mouth_open_ratio=round(mouth_open_ratio, 4),
            lip_compression=round(lip_compression, 3),
            is_smiling=is_smiling,
        )

    def _detect_speaking(self) -> bool:
        if len(self._mouth_ratio_history) < self._mouth_ratio_history.maxlen:
            return False
        values = list(self._mouth_ratio_history)
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return variance > self.speaking_variance_threshold

    def reset(self) -> None:
        self._mouth_ratio_history.clear()
