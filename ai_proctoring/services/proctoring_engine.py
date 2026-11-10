"""
ProctoringEngine

Turns raw per-frame metrics into discrete, human-readable warnings (the ones
surfaced live to the candidate/proctor UI) and an aggregate Suspicious
Activity Score for the frame. Uses debouncing (a violation must persist for
a minimum number of consecutive frames) to avoid flooding the UI/log with
one-frame noise from normal, momentary head movement.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from models.schemas import (
    DetectedObject,
    FaceQuality,
    GazeDirection,
    HeadPoseMetrics,
    ReadingMetrics,
    WarningEvent,
    WarningSeverity,
    WarningType,
)


class ProctoringEngine:
    def __init__(self, debounce_frames: int = 8) -> None:
        self.debounce_frames = debounce_frames
        self._consecutive_counts: Dict[WarningType, int] = defaultdict(int)
        self._already_warned: Dict[WarningType, bool] = defaultdict(bool)

    def evaluate(
        self,
        frame_index: int,
        face_quality: FaceQuality,
        gaze_direction: GazeDirection,
        head_pose: HeadPoseMetrics,
        reading: ReadingMetrics,
        objects: List[DetectedObject],
        client_fullscreen_exit: bool = False,
    ) -> tuple[list[WarningEvent], float]:
        raw_flags: Dict[WarningType, tuple[WarningSeverity, str]] = {}

        if face_quality.faces_detected == 0:
            raw_flags[WarningType.NO_FACE] = (
                WarningSeverity.CRITICAL, "Face is not visible. Please stay in front of the camera."
            )
        elif face_quality.faces_detected > 1:
            raw_flags[WarningType.MULTIPLE_FACES] = (
                WarningSeverity.CRITICAL, "Multiple faces detected in the frame."
            )
        elif not face_quality.face_visible or face_quality.quality_score < 40:
            raw_flags[WarningType.LOW_FACE_QUALITY] = (
                WarningSeverity.WARNING, "Face is not clearly visible. Adjust lighting or camera position."
            )

        if face_quality.faces_detected == 1 and gaze_direction not in (GazeDirection.CENTER,):
            raw_flags[WarningType.LOOKING_AWAY] = (
                WarningSeverity.WARNING, "Please look at the camera / screen."
            )

        if reading.reading_probability >= 65:
            raw_flags[WarningType.POSSIBLE_READING] = (
                WarningSeverity.WARNING, "Reading pattern detected - possible use of notes or another screen."
            )

        if abs(head_pose.yaw) > 35 or abs(head_pose.pitch) > 30:
            raw_flags[WarningType.EXCESSIVE_HEAD_MOVEMENT] = (
                WarningSeverity.INFO, "Excessive head movement detected."
            )

        if objects:
            labels = ", ".join(sorted({o.label for o in objects}))
            raw_flags[WarningType.SUSPICIOUS_OBJECT] = (
                WarningSeverity.CRITICAL, f"Suspicious object detected: {labels}."
            )

        if client_fullscreen_exit:
            raw_flags[WarningType.FULLSCREEN_EXIT] = (
                WarningSeverity.WARNING, "Candidate exited fullscreen mode."
            )

        active_types = set(raw_flags.keys())
        confirmed_warnings: List[WarningEvent] = []

        tracked_types = set(self._consecutive_counts.keys()) | active_types
        for warning_type in tracked_types:
            if warning_type in active_types:
                self._consecutive_counts[warning_type] += 1
            else:
                self._consecutive_counts[warning_type] = 0
                self._already_warned[warning_type] = False
                continue

            if self._consecutive_counts[warning_type] >= self.debounce_frames:
                severity, message = raw_flags[warning_type]
                confirmed_warnings.append(WarningEvent(
                    type=warning_type, severity=severity, message=message, frame_index=frame_index,
                ))

        suspicious_score = self._suspicious_score(confirmed_warnings, active_types)
        return confirmed_warnings, suspicious_score

    @staticmethod
    def _suspicious_score(confirmed: List[WarningEvent], active_types: set) -> float:
        weight_map = {
            WarningType.NO_FACE: 20.0,
            WarningType.MULTIPLE_FACES: 35.0,
            WarningType.LOOKING_AWAY: 8.0,
            WarningType.POSSIBLE_READING: 18.0,
            WarningType.PERSON_LEFT_FRAME: 25.0,
            WarningType.LOW_FACE_QUALITY: 4.0,
            WarningType.SUSPICIOUS_OBJECT: 30.0,
            WarningType.FULLSCREEN_EXIT: 15.0,
            WarningType.EXCESSIVE_HEAD_MOVEMENT: 5.0,
        }
        score = sum(weight_map.get(w.type, 5.0) for w in confirmed)
        return min(100.0, score)

    def reset(self) -> None:
        self._consecutive_counts.clear()
        self._already_warned.clear()
