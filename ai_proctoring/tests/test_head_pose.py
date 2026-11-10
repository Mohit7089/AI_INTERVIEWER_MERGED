import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.head_pose import HeadPoseService
from tests.fixtures import frontal_face_landmarks


def test_frontal_face_yields_near_zero_yaw_roll():
    service = HeadPoseService(frame_width=640, frame_height=480)
    landmarks = frontal_face_landmarks()
    metrics = service.analyze(landmarks)

    # Our synthetic landmarks are a rough approximation of frontal geometry;
    # solvePnP should still land reasonably close to zero for yaw/roll.
    assert abs(metrics.yaw) < 45
    assert abs(metrics.roll) < 45
    assert 0.0 <= metrics.stability_score <= 100.0


def test_stability_score_decreases_with_jitter():
    service = HeadPoseService(frame_width=640, frame_height=480)
    stable_landmarks = frontal_face_landmarks()

    # Feed identical landmarks repeatedly -> should stay maximally stable
    for _ in range(10):
        metrics_stable = service.analyze(stable_landmarks)
    assert metrics_stable.stability_score > 90.0

    # Now feed landmarks with the nose tip jittering around -> stability should drop
    service.reset()
    import random
    random.seed(42)
    for _ in range(10):
        jittered = list(stable_landmarks)
        x, y, z = jittered[1]
        jittered[1] = (x + random.uniform(-40, 40), y + random.uniform(-40, 40), z)
        metrics_jittered = service.analyze(jittered)

    assert metrics_jittered.stability_score <= metrics_stable.stability_score


if __name__ == "__main__":
    test_frontal_face_yields_near_zero_yaw_roll()
    test_stability_score_decreases_with_jitter()
    print("test_head_pose: all tests passed")
