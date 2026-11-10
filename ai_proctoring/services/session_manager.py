"""
SessionManager

Owns one `SessionPipeline` per active interview/proctoring session. Each
pipeline holds its own stateful service instances (FaceMesh, Pose, eye
tracker, blink counter, head-pose stability window, etc.) so concurrent
interviews never share or corrupt each other's rolling state.

This is the orchestration layer: `process_frame()` runs the full
Webcam -> FaceMesh/Pose -> Feature Extraction -> Behavior Analysis ->
Proctoring Engine pipeline described in the architecture diagram, for a
single incoming frame, and returns one `FrameAnalysisResult`.

It also incrementally aggregates statistics needed for the final report, so
report generation is O(1) lookup rather than re-processing raw frames.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np

from config.settings import get_settings
from models.schemas import (
    ClientEventMessage,
    FaceQuality,
    FrameAnalysisResult,
    GazeDirection,
    SessionReport,
    SessionStatus,
    TimelinePoint,
    WarningEvent,
)
from services.behavior_engine import BehaviorEngine
from services.blink_analysis import BlinkAnalysisService
from services.eye_tracking import EyeTrackingService
from services.face_mesh_service import FaceMeshService
from services.head_pose import HeadPoseService
from services.lip_analysis import LipAnalysisService
from services.object_detection import ObjectDetectionService
from services.pose_service import PoseService
from services.posture_analysis import PostureAnalysisService
from services.proctoring_engine import ProctoringEngine
from services.reading_detection import ReadingDetectionService
from utils.image_utils import resize_frame
from utils.logger import logger

_settings = get_settings()


@dataclass
class _Aggregates:
    frames_analyzed: int = 0
    sum_eye_contact: float = 0.0
    sum_confidence: float = 0.0
    sum_calmness: float = 0.0
    sum_stress: float = 0.0
    sum_professionalism: float = 0.0
    sum_attention: float = 0.0
    sum_engagement: float = 0.0
    sum_posture: float = 0.0
    sum_head_stability: float = 0.0
    sum_reading_probability: float = 0.0
    violation_log: List[WarningEvent] = field(default_factory=list)
    timeline: List[TimelinePoint] = field(default_factory=list)
    last_blink_count: int = 0
    last_blink_rate: float = 0.0
    last_fatigue_score: float = 0.0


class SessionPipeline:
    def __init__(self, session_id: str, interview_id: str, user_id: str,
                 candidate_name: Optional[str] = None) -> None:
        self.session_id = session_id
        self.interview_id = interview_id
        self.user_id = user_id
        self.candidate_name = candidate_name
        self.started_at = datetime.utcnow()
        self.ended_at: Optional[datetime] = None
        self.status = SessionStatus.ACTIVE

        self.face_mesh = FaceMeshService()
        self.pose = PoseService()
        self.eye_tracker = EyeTrackingService()
        self.blink_analyzer = BlinkAnalysisService()
        self.lip_analyzer = LipAnalysisService()
        self.posture_analyzer = PostureAnalysisService()
        self.reading_detector = ReadingDetectionService()
        self.object_detector = ObjectDetectionService()
        self.behavior_engine = BehaviorEngine()
        self.proctoring_engine = ProctoringEngine()

        self._head_pose_service: Optional[HeadPoseService] = None  # needs frame dims, built lazily
        self.frame_index = 0
        self.aggregates = _Aggregates()
        self._fullscreen_exit_flag = False

    def handle_client_event(self, event: ClientEventMessage) -> None:
        if event.event == "fullscreen_exit":
            self._fullscreen_exit_flag = True
            logger.info(f"[{self.session_id}] fullscreen exit reported by client")

    def process_frame(self, frame_bgr: np.ndarray) -> FrameAnalysisResult:
        self.frame_index += 1
        frame_bgr = resize_frame(frame_bgr, _settings.max_frame_width)
        h, w = frame_bgr.shape[:2]

        if self._head_pose_service is None:
            self._head_pose_service = HeadPoseService(w, h)

        mesh_output = self.face_mesh.process(frame_bgr)
        result = FrameAnalysisResult(
            session_id=self.session_id, frame_index=self.frame_index, face_quality=mesh_output.quality,
        )

        objects = []
        if _settings.enable_object_detection and self.frame_index % _settings.object_detection_every_n == 0:
            objects = self.object_detector.detect(frame_bgr)
        result.objects = objects

        if mesh_output.faces_pixel_landmarks:
            primary_face = max(
                mesh_output.faces_pixel_landmarks,
                key=lambda pts: self._face_bbox_area(pts),
            )
            result.eye = self.eye_tracker.analyze(primary_face)
            result.head_pose = self._head_pose_service.analyze(primary_face)
            result.blink = self.blink_analyzer.analyze(result.eye.avg_ear)
            result.lip = self.lip_analyzer.analyze(primary_face)
            result.reading = self.reading_detector.analyze(
                result.eye.gaze_x, result.eye.gaze_y, result.head_pose.yaw, result.head_pose.pitch
            )
        else:
            # No face -> neutral/attention-penalizing defaults so downstream scores reflect it
            result.eye.is_looking_at_camera = False
            result.eye.eye_contact_score = 0.0

        pose_output = self.pose.process(frame_bgr)
        if pose_output.pose_detected and pose_output.landmarks_px:
            result.posture = self.posture_analyzer.analyze(pose_output.landmarks_px, w)

        result.behavior = self.behavior_engine.score(
            result.eye, result.head_pose, result.blink, result.lip, result.posture, result.reading,
        )

        warnings, suspicious_score = self.proctoring_engine.evaluate(
            frame_index=self.frame_index,
            face_quality=result.face_quality,
            gaze_direction=result.eye.gaze_direction,
            head_pose=result.head_pose,
            reading=result.reading,
            objects=objects,
            client_fullscreen_exit=self._fullscreen_exit_flag,
        )
        self._fullscreen_exit_flag = False
        result.warnings = warnings
        result.suspicious_activity_score = suspicious_score

        self._update_aggregates(result)
        return result

    @staticmethod
    def _face_bbox_area(pts) -> float:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (max(xs) - min(xs)) * (max(ys) - min(ys))

    def _update_aggregates(self, result: FrameAnalysisResult) -> None:
        agg = self.aggregates
        agg.frames_analyzed += 1
        agg.sum_eye_contact += result.eye.eye_contact_score
        agg.sum_confidence += result.behavior.confidence
        agg.sum_calmness += result.behavior.calmness
        agg.sum_stress += result.behavior.stress
        agg.sum_professionalism += result.behavior.professionalism
        agg.sum_attention += result.behavior.attention
        agg.sum_engagement += result.behavior.engagement
        agg.sum_posture += result.posture.professionalism_score
        agg.sum_head_stability += result.head_pose.stability_score
        agg.sum_reading_probability += result.reading.reading_probability
        agg.last_blink_count = result.blink.blink_count
        agg.last_blink_rate = result.blink.blink_rate_per_min
        agg.last_fatigue_score = result.blink.fatigue_score
        agg.violation_log.extend(result.warnings)

        # Sample the timeline roughly once per second's worth of frames (approx,
        # since actual fps varies with client throttling) to keep the report light.
        if agg.frames_analyzed % 15 == 0:
            agg.timeline.append(TimelinePoint(
                timestamp=result.timestamp,
                eye_contact_score=result.eye.eye_contact_score,
                attention=result.behavior.attention,
                stress=result.behavior.stress,
                suspicious_activity_score=result.suspicious_activity_score,
            ))

    def build_report(self) -> SessionReport:
        agg = self.aggregates
        n = max(1, agg.frames_analyzed)
        duration = (
            (self.ended_at or datetime.utcnow()) - self.started_at
        ).total_seconds()

        avg = lambda total: round(total / n, 1)  # noqa: E731

        overall_score = round(
            0.25 * (agg.sum_eye_contact / n)
            + 0.2 * (agg.sum_professionalism / n)
            + 0.2 * (agg.sum_attention / n)
            + 0.15 * (agg.sum_confidence / n)
            + 0.2 * max(0.0, 100.0 - (agg.sum_stress / n)),
            1,
        )

        recommendations = self._build_recommendations(agg, n)
        recruiter_summary = self._build_recruiter_summary(agg, n, overall_score)
        candidate_feedback = self._build_candidate_feedback(agg, n)

        return SessionReport(
            session_id=self.session_id,
            interview_id=self.interview_id,
            user_id=self.user_id,
            candidate_name=self.candidate_name,
            started_at=self.started_at,
            ended_at=self.ended_at or datetime.utcnow(),
            duration_seconds=round(duration, 1),
            status=self.status,
            frames_analyzed=agg.frames_analyzed,
            overall_score=overall_score,
            eye_contact_percentage=avg(agg.sum_eye_contact),
            confidence=avg(agg.sum_confidence),
            calmness=avg(agg.sum_calmness),
            stress=avg(agg.sum_stress),
            professionalism=avg(agg.sum_professionalism),
            attention=avg(agg.sum_attention),
            communication_proxy=avg(agg.sum_engagement),
            posture_score=avg(agg.sum_posture),
            blink_count=agg.last_blink_count,
            avg_blink_rate=agg.last_blink_rate,
            fatigue_score=agg.last_fatigue_score,
            avg_head_stability=avg(agg.sum_head_stability),
            avg_reading_probability=avg(agg.sum_reading_probability),
            suspicious_events_count=len(agg.violation_log),
            violation_log=agg.violation_log,
            timeline=agg.timeline,
            recommendations=recommendations,
            recruiter_summary=recruiter_summary,
            candidate_feedback=candidate_feedback,
        )

    @staticmethod
    def _build_recommendations(agg: _Aggregates, n: int) -> List[str]:
        recs: List[str] = []
        if agg.sum_eye_contact / n < 60:
            recs.append("Practice maintaining consistent eye contact with the camera during responses.")
        if agg.sum_reading_probability / n > 40:
            recs.append("Reduce reliance on notes; rehearsing answers out loud can help with recall under pressure.")
        if agg.sum_posture / n < 65:
            recs.append("Sit upright and keep shoulders level to project a more professional presence on camera.")
        if agg.sum_stress / n > 60:
            recs.append("Consider relaxation techniques (breathing exercises, brief pauses) to reduce visible tension.")
        if agg.last_fatigue_score > 50:
            recs.append("Ensure adequate rest before interviews; blink patterns suggest fatigue.")
        if not recs:
            recs.append("Overall behavior was strong and professional. Keep up consistent habits in future interviews.")
        return recs

    @staticmethod
    def _build_recruiter_summary(agg: _Aggregates, n: int, overall_score: float) -> str:
        critical_events = [w for w in agg.violation_log if w.severity.value == "critical"]
        parts = [f"Overall behavioral score: {overall_score}/100 across {n} analyzed frames."]
        if critical_events:
            parts.append(f"{len(critical_events)} critical proctoring event(s) were flagged during the session.")
        else:
            parts.append("No critical proctoring violations were detected.")
        parts.append(
            f"Average eye contact {round(agg.sum_eye_contact / n, 1)}%, "
            f"attention {round(agg.sum_attention / n, 1)}/100, "
            f"professionalism {round(agg.sum_professionalism / n, 1)}/100."
        )
        return " ".join(parts)

    @staticmethod
    def _build_candidate_feedback(agg: _Aggregates, n: int) -> str:
        eye_contact = agg.sum_eye_contact / n
        stress = agg.sum_stress / n
        if eye_contact >= 75 and stress <= 40:
            return "You maintained strong eye contact and appeared calm and composed throughout the interview. Great job!"
        if eye_contact < 50:
            return "Try to look at the camera more consistently — this helps convey confidence and engagement to the interviewer."
        if stress > 60:
            return "You appeared a little tense at times. A few deep breaths before answering can help you feel more at ease."
        return "You showed steady, professional behavior overall. Keep practicing to build even more consistency."

    def close(self) -> None:
        self.face_mesh.close()
        self.pose.close()
        self.ended_at = datetime.utcnow()


class SessionManager:
    """Process-wide registry of active session pipelines."""

    def __init__(self) -> None:
        self._sessions: Dict[str, SessionPipeline] = {}

    def create_session(self, interview_id: str, user_id: str, candidate_name: Optional[str] = None) -> SessionPipeline:
        session_id = str(uuid.uuid4())
        pipeline = SessionPipeline(session_id, interview_id, user_id, candidate_name)
        self._sessions[session_id] = pipeline
        logger.info(f"Created proctoring session {session_id} for interview {interview_id}")
        return pipeline

    def get_session(self, session_id: str) -> Optional[SessionPipeline]:
        return self._sessions.get(session_id)

    def end_session(self, session_id: str) -> Optional[SessionPipeline]:
        pipeline = self._sessions.get(session_id)
        if pipeline is None:
            return None
        pipeline.status = SessionStatus.COMPLETED
        pipeline.close()
        return pipeline

    def remove_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


# Process-wide singleton (fine for a single-instance FastAPI deployment;
# for horizontal scaling, back this with a shared store keyed by session_id
# and route WebSocket connections with session affinity/sticky routing).
session_manager = SessionManager()
