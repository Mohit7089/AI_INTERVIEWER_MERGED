"""
Pydantic schemas — the data contracts shared between the CV pipeline,
the WebSocket layer, the REST API, and MongoDB persistence.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class GazeDirection(str, Enum):
    CENTER = "center"
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"
    AWAY = "away"


class WarningType(str, Enum):
    NO_FACE = "no_face_detected"
    MULTIPLE_FACES = "multiple_faces_detected"
    LOOKING_AWAY = "looking_away"
    POSSIBLE_READING = "possible_reading"
    PERSON_LEFT_FRAME = "person_left_frame"
    LOW_FACE_QUALITY = "low_face_quality"
    SUSPICIOUS_OBJECT = "suspicious_object_detected"
    FULLSCREEN_EXIT = "fullscreen_exit"
    EXCESSIVE_HEAD_MOVEMENT = "excessive_head_movement"


class WarningSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABORTED = "aborted"


# ---------------------------------------------------------------------------
# Per-frame analysis payloads
# ---------------------------------------------------------------------------

class EyeMetrics(BaseModel):
    left_ear: float = 0.0
    right_ear: float = 0.0
    avg_ear: float = 0.0
    gaze_direction: GazeDirection = GazeDirection.CENTER
    gaze_x: float = 0.0          # normalized horizontal gaze offset, -1 (left) .. 1 (right)
    gaze_y: float = 0.0          # normalized vertical gaze offset, -1 (up) .. 1 (down)
    is_looking_at_camera: bool = True
    eye_contact_score: float = 100.0


class HeadPoseMetrics(BaseModel):
    pitch: float = 0.0
    yaw: float = 0.0
    roll: float = 0.0
    stability_score: float = 100.0


class BlinkMetrics(BaseModel):
    blink_count: int = 0
    blink_rate_per_min: float = 0.0
    is_long_blink: bool = False
    is_rapid_blink: bool = False
    fatigue_score: float = 0.0   # 0 = alert, 100 = very fatigued


class LipMetrics(BaseModel):
    is_speaking: bool = False
    mouth_open_ratio: float = 0.0
    lip_compression: float = 0.0
    is_smiling: bool = False


class PostureMetrics(BaseModel):
    is_leaning: bool = False
    is_slouching: bool = False
    shoulder_tilt_deg: float = 0.0
    head_tilt_deg: float = 0.0
    posture_label: str = "straight"
    professionalism_score: float = 100.0


class ReadingMetrics(BaseModel):
    reading_probability: float = 0.0   # 0-100 %
    horizontal_scan_detected: bool = False
    vertical_scan_detected: bool = False
    fixation_detected: bool = False


class BehaviorScores(BaseModel):
    confidence: float = 50.0
    calmness: float = 50.0
    nervousness: float = 50.0
    attention: float = 50.0
    engagement: float = 50.0
    professionalism: float = 50.0
    stress: float = 50.0


class DetectedObject(BaseModel):
    label: str
    confidence: float
    bbox: List[float]  # [x1, y1, x2, y2]


class FaceQuality(BaseModel):
    faces_detected: int = 0
    face_visible: bool = False
    brightness_ok: bool = True
    face_size_ratio: float = 0.0   # fraction of frame area occupied by face bbox
    quality_score: float = 100.0


class WarningEvent(BaseModel):
    type: WarningType
    severity: WarningSeverity
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    frame_index: int = 0


class FrameAnalysisResult(BaseModel):
    """Full result of analyzing a single webcam frame."""
    session_id: str
    frame_index: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    face_quality: FaceQuality = Field(default_factory=FaceQuality)
    eye: EyeMetrics = Field(default_factory=EyeMetrics)
    head_pose: HeadPoseMetrics = Field(default_factory=HeadPoseMetrics)
    blink: BlinkMetrics = Field(default_factory=BlinkMetrics)
    lip: LipMetrics = Field(default_factory=LipMetrics)
    posture: PostureMetrics = Field(default_factory=PostureMetrics)
    reading: ReadingMetrics = Field(default_factory=ReadingMetrics)
    behavior: BehaviorScores = Field(default_factory=BehaviorScores)
    objects: List[DetectedObject] = Field(default_factory=list)

    warnings: List[WarningEvent] = Field(default_factory=list)
    suspicious_activity_score: float = 0.0  # 0 = clean, 100 = highly suspicious


# ---------------------------------------------------------------------------
# Session-level API payloads
# ---------------------------------------------------------------------------

class StartSessionRequest(BaseModel):
    interview_id: str
    user_id: str
    candidate_name: Optional[str] = None


class StartSessionResponse(BaseModel):
    session_id: str
    websocket_url: str


class ClientFrameMessage(BaseModel):
    type: str = "frame"
    image: str  # base64 data-URL
    frame_index: int


class ClientEventMessage(BaseModel):
    """Non-frame client signals, e.g. tab/fullscreen changes detected in-browser."""
    type: str = "event"
    event: str  # "fullscreen_exit" | "tab_blur" | ...


class ServerAnalysisMessage(BaseModel):
    type: str = "analysis"
    result: FrameAnalysisResult


class ServerWarningMessage(BaseModel):
    type: str = "warning"
    warning: WarningEvent


# ---------------------------------------------------------------------------
# Aggregate report
# ---------------------------------------------------------------------------

class TimelinePoint(BaseModel):
    timestamp: datetime
    eye_contact_score: float
    attention: float
    stress: float
    suspicious_activity_score: float


class SessionReport(BaseModel):
    session_id: str
    interview_id: str
    user_id: str
    candidate_name: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    status: SessionStatus = SessionStatus.ACTIVE
    frames_analyzed: int = 0

    overall_score: float = 0.0
    eye_contact_percentage: float = 0.0
    confidence: float = 0.0
    calmness: float = 0.0
    stress: float = 0.0
    professionalism: float = 0.0
    attention: float = 0.0
    communication_proxy: float = 0.0
    posture_score: float = 0.0

    blink_count: int = 0
    avg_blink_rate: float = 0.0
    fatigue_score: float = 0.0

    avg_head_stability: float = 0.0
    avg_reading_probability: float = 0.0

    suspicious_events_count: int = 0
    violation_log: List[WarningEvent] = Field(default_factory=list)
    timeline: List[TimelinePoint] = Field(default_factory=list)

    recommendations: List[str] = Field(default_factory=list)
    recruiter_summary: str = ""
    candidate_feedback: str = ""

    pdf_path: Optional[str] = None
