"""
PoseService: thin wrapper around MediaPipe Pose used for upper-body posture
analysis (shoulders, hips proxy, head-to-shoulder alignment).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np


@dataclass
class PoseOutput:
    landmarks_px: Optional[List[Tuple[float, float, float, float]]]  # (x, y, z, visibility)
    pose_detected: bool


class PoseService:
    # Indices we care about from mp.solutions.pose.PoseLandmark
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_EAR = 7
    RIGHT_EAR = 8
    NOSE = 0
    LEFT_HIP = 23
    RIGHT_HIP = 24

    def __init__(self, min_detection_confidence: float = 0.5, min_tracking_confidence: float = 0.5) -> None:
        self._mp_pose = mp.solutions.pose
        self._pose = self._mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def process(self, frame_bgr: np.ndarray) -> PoseOutput:
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self._pose.process(rgb)

        if not results.pose_landmarks:
            return PoseOutput(landmarks_px=None, pose_detected=False)

        pts = [
            (lm.x * w, lm.y * h, lm.z * w, lm.visibility)
            for lm in results.pose_landmarks.landmark
        ]
        return PoseOutput(landmarks_px=pts, pose_detected=True)

    def close(self) -> None:
        self._pose.close()
