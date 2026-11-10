import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.schemas import FaceQuality, GazeDirection, HeadPoseMetrics, ReadingMetrics, WarningType
from services.proctoring_engine import ProctoringEngine


def test_no_face_warning_after_debounce():
    engine = ProctoringEngine(debounce_frames=3)
    face_quality = FaceQuality(faces_detected=0, face_visible=False, quality_score=0.0)
    head_pose = HeadPoseMetrics()
    reading = ReadingMetrics()

    warnings = []
    for i in range(1, 5):
        warnings, score = engine.evaluate(i, face_quality, GazeDirection.CENTER, head_pose, reading, [])

    types = {w.type for w in warnings}
    assert WarningType.NO_FACE in types


def test_no_warning_before_debounce_threshold():
    engine = ProctoringEngine(debounce_frames=5)
    face_quality = FaceQuality(faces_detected=0, face_visible=False, quality_score=0.0)
    head_pose = HeadPoseMetrics()
    reading = ReadingMetrics()

    warnings, score = engine.evaluate(1, face_quality, GazeDirection.CENTER, head_pose, reading, [])
    assert len(warnings) == 0


def test_multiple_faces_triggers_critical_warning():
    engine = ProctoringEngine(debounce_frames=2)
    face_quality = FaceQuality(faces_detected=2, face_visible=True, quality_score=90.0)
    head_pose = HeadPoseMetrics()
    reading = ReadingMetrics()

    warnings = []
    for i in range(1, 4):
        warnings, score = engine.evaluate(i, face_quality, GazeDirection.CENTER, head_pose, reading, [])

    types = {w.type for w in warnings}
    assert WarningType.MULTIPLE_FACES in types
    assert score > 0


def test_clean_session_has_zero_suspicious_score():
    engine = ProctoringEngine(debounce_frames=2)
    face_quality = FaceQuality(faces_detected=1, face_visible=True, quality_score=95.0)
    head_pose = HeadPoseMetrics(yaw=2.0, pitch=1.0)
    reading = ReadingMetrics(reading_probability=5.0)

    warnings, score = engine.evaluate(1, face_quality, GazeDirection.CENTER, head_pose, reading, [])
    assert score == 0.0
    assert len(warnings) == 0


def test_each_warning_type_reported_only_once_per_frame():
    """Regression test: a persistently-active violation must appear exactly
    once in the confirmed warnings list for a given frame, not duplicated."""
    engine = ProctoringEngine(debounce_frames=2)
    face_quality = FaceQuality(faces_detected=0, face_visible=False, quality_score=0.0)
    head_pose = HeadPoseMetrics()
    reading = ReadingMetrics()

    warnings = []
    for i in range(1, 6):
        warnings, score = engine.evaluate(i, face_quality, GazeDirection.CENTER, head_pose, reading, [])

    no_face_warnings = [w for w in warnings if w.type == WarningType.NO_FACE]
    assert len(no_face_warnings) == 1


if __name__ == "__main__":
    test_no_face_warning_after_debounce()
    test_no_warning_before_debounce_threshold()
    test_multiple_faces_triggers_critical_warning()
    test_clean_session_has_zero_suspicious_score()
    test_each_warning_type_reported_only_once_per_frame()
    print("test_proctoring_engine: all tests passed")
