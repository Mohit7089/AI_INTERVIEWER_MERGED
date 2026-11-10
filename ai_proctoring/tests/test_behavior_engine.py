import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.schemas import (
    BlinkMetrics, EyeMetrics, GazeDirection, HeadPoseMetrics, LipMetrics,
    PostureMetrics, ReadingMetrics,
)
from services.behavior_engine import BehaviorEngine


def _good_metrics():
    eye = EyeMetrics(eye_contact_score=95, gaze_direction=GazeDirection.CENTER, is_looking_at_camera=True)
    head_pose = HeadPoseMetrics(stability_score=95)
    blink = BlinkMetrics(is_rapid_blink=False, blink_rate_per_min=16)
    lip = LipMetrics(lip_compression=0.05, is_speaking=True)
    posture = PostureMetrics(professionalism_score=95)
    reading = ReadingMetrics(reading_probability=5)
    return eye, head_pose, blink, lip, posture, reading


def _poor_metrics():
    eye = EyeMetrics(eye_contact_score=20, gaze_direction=GazeDirection.AWAY, is_looking_at_camera=False)
    head_pose = HeadPoseMetrics(stability_score=30)
    blink = BlinkMetrics(is_rapid_blink=True, blink_rate_per_min=35)
    lip = LipMetrics(lip_compression=0.8, is_speaking=False)
    posture = PostureMetrics(professionalism_score=40)
    reading = ReadingMetrics(reading_probability=80)
    return eye, head_pose, blink, lip, posture, reading


def test_good_behavior_scores_higher_than_poor_behavior():
    engine = BehaviorEngine()
    good_scores = engine.score(*_good_metrics())
    poor_scores = engine.score(*_poor_metrics())

    assert good_scores.confidence > poor_scores.confidence
    assert good_scores.attention > poor_scores.attention
    assert good_scores.calmness > poor_scores.calmness
    assert good_scores.stress < poor_scores.stress
    assert good_scores.professionalism > poor_scores.professionalism


def test_scores_are_bounded_0_to_100():
    engine = BehaviorEngine()
    for metrics in (_good_metrics(), _poor_metrics()):
        scores = engine.score(*metrics)
        for value in scores.model_dump().values():
            assert 0.0 <= value <= 100.0


if __name__ == "__main__":
    test_good_behavior_scores_higher_than_poor_behavior()
    test_scores_are_bounded_0_to_100()
    print("test_behavior_engine: all tests passed")
