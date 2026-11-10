import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.schemas import GazeDirection
from services.eye_tracking import EyeTrackingService
from tests.fixtures import frontal_face_landmarks


def test_ear_open_eyes_greater_than_closed():
    service = EyeTrackingService()
    open_landmarks = frontal_face_landmarks(eyes_open=True)
    closed_landmarks = frontal_face_landmarks(eyes_open=False)

    open_metrics = service.analyze(open_landmarks)
    service.reset()
    closed_metrics = service.analyze(closed_landmarks)

    assert open_metrics.avg_ear > closed_metrics.avg_ear
    assert open_metrics.avg_ear > 0.15
    assert closed_metrics.avg_ear < 0.18


def test_centered_gaze_classified_as_center():
    service = EyeTrackingService()
    landmarks = frontal_face_landmarks(eyes_open=True)
    metrics = service.analyze(landmarks)
    assert metrics.gaze_direction == GazeDirection.CENTER
    assert metrics.is_looking_at_camera is True


def test_eye_contact_score_rolls_up_over_frames():
    service = EyeTrackingService(eye_contact_window=5)
    landmarks = frontal_face_landmarks(eyes_open=True)
    for _ in range(5):
        metrics = service.analyze(landmarks)
    assert metrics.eye_contact_score == 100.0


if __name__ == "__main__":
    test_ear_open_eyes_greater_than_closed()
    test_centered_gaze_classified_as_center()
    test_eye_contact_score_rolls_up_over_frames()
    print("test_eye_tracking: all tests passed")
