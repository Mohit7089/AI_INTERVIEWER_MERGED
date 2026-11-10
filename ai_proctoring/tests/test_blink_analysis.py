import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.blink_analysis import BlinkAnalysisService


def test_single_blink_is_counted_on_reopen():
    service = BlinkAnalysisService(ear_closed_threshold=0.18)
    # eyes open -> closed -> closed -> open  == exactly 1 blink
    service.analyze(0.30)
    service.analyze(0.10)
    service.analyze(0.09)
    metrics = service.analyze(0.30)
    assert metrics.blink_count == 1


def test_long_blink_detected_after_many_closed_frames():
    service = BlinkAnalysisService(ear_closed_threshold=0.18, long_blink_frames=5)
    service.analyze(0.30)
    for _ in range(8):
        service.analyze(0.05)
    metrics = service.analyze(0.30)
    assert metrics.blink_count == 1
    assert metrics.is_long_blink is True


def test_rapid_blink_flag_after_many_quick_blinks():
    service = BlinkAnalysisService(rapid_blink_window_s=10.0, rapid_blink_count=3)
    metrics = None
    for _ in range(3):
        service.analyze(0.30)
        service.analyze(0.05)
        metrics = service.analyze(0.30)
    assert metrics.is_rapid_blink is True
    assert metrics.fatigue_score >= 0.0


if __name__ == "__main__":
    test_single_blink_is_counted_on_reopen()
    test_long_blink_detected_after_many_closed_frames()
    test_rapid_blink_flag_after_many_quick_blinks()
    print("test_blink_analysis: all tests passed")
