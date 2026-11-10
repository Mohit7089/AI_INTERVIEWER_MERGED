"""
PostureAnalysisService

Uses MediaPipe Pose upper-body landmarks (shoulders, ears, nose) to derive:
  - Shoulder tilt (roll of the shoulder line)
  - Head tilt (roll of the ear-to-ear line, correlated with shoulder tilt to
    catch "leaning" separately from "head cocked")
  - Leaning: horizontal displacement of shoulder midpoint from frame center,
    or shoulders moving significantly closer to camera (a rough proxy since
    we don't have real depth) -- combined with a forward-lean estimate from
    the nose-to-shoulder-midpoint vertical gap shrinking.
  - Slouching: reduced vertical distance between ears and shoulders relative
    to a running baseline (candidate sinking down / curling forward).
  - A composite Professionalism Score.
"""
from __future__ import annotations

import math
from collections import deque
from typing import Deque, List, Optional, Tuple

from models.schemas import PostureMetrics
from services.pose_service import PoseService
from utils.geometry import euclidean_distance

PointVis = Tuple[float, float, float, float]


class PostureAnalysisService:
    def __init__(self, baseline_window: int = 60) -> None:
        # Running baseline of "ear-to-shoulder" vertical distance while seated
        # normally, established from the first `baseline_window` good frames.
        self._baseline_distances: Deque[float] = deque(maxlen=baseline_window)
        self._baseline_locked: Optional[float] = None

    def analyze(self, pose_landmarks: List[PointVis], frame_width: int) -> PostureMetrics:
        ls = pose_landmarks[PoseService.LEFT_SHOULDER]
        rs = pose_landmarks[PoseService.RIGHT_SHOULDER]
        le = pose_landmarks[PoseService.LEFT_EAR]
        re = pose_landmarks[PoseService.RIGHT_EAR]
        nose = pose_landmarks[PoseService.NOSE]

        visible_enough = min(ls[3], rs[3]) > 0.4
        if not visible_enough:
            return PostureMetrics(posture_label="unknown", professionalism_score=70.0)

        shoulder_mid = ((ls[0] + rs[0]) / 2.0, (ls[1] + rs[1]) / 2.0)
        ear_mid = ((le[0] + re[0]) / 2.0, (le[1] + re[1]) / 2.0)

        shoulder_tilt_deg = math.degrees(math.atan2(rs[1] - ls[1], rs[0] - ls[0]))
        head_tilt_deg = math.degrees(math.atan2(re[1] - le[1], re[0] - le[0]))

        vertical_gap = shoulder_mid[1] - ear_mid[1]  # positive: ears above shoulders (normal)
        if self._baseline_locked is None:
            self._baseline_distances.append(vertical_gap)
            if len(self._baseline_distances) >= self._baseline_distances.maxlen:
                self._baseline_locked = sum(self._baseline_distances) / len(self._baseline_distances)
            baseline = vertical_gap
        else:
            baseline = self._baseline_locked

        slouch_ratio = (baseline - vertical_gap) / baseline if baseline > 1e-3 else 0.0
        is_slouching = slouch_ratio > 0.18  # ears dropped notably closer to shoulders

        horizontal_offset = abs(nose[0] - shoulder_mid[0])
        shoulder_width = max(euclidean_distance(ls[:2], rs[:2]), 1.0)
        lean_ratio = horizontal_offset / shoulder_width
        is_leaning = lean_ratio > 0.35 or abs(shoulder_tilt_deg) > 12.0

        label = "straight"
        if is_slouching:
            label = "slouching"
        elif is_leaning:
            label = "leaning"

        professionalism_score = self._score(shoulder_tilt_deg, head_tilt_deg, is_slouching, is_leaning)

        return PostureMetrics(
            is_leaning=is_leaning,
            is_slouching=is_slouching,
            shoulder_tilt_deg=round(shoulder_tilt_deg, 2),
            head_tilt_deg=round(head_tilt_deg, 2),
            posture_label=label,
            professionalism_score=round(professionalism_score, 1),
        )

    @staticmethod
    def _score(shoulder_tilt: float, head_tilt: float, slouching: bool, leaning: bool) -> float:
        score = 100.0
        score -= min(30.0, abs(shoulder_tilt) * 1.5)
        score -= min(20.0, abs(head_tilt) * 1.0)
        if slouching:
            score -= 25.0
        if leaning:
            score -= 15.0
        return max(0.0, min(100.0, score))

    def reset(self) -> None:
        self._baseline_distances.clear()
        self._baseline_locked = None
