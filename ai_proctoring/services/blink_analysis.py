"""
BlinkAnalysisService

Detects blinks from the EAR signal using a simple state machine (eye-closed
run-length), then derives:
  - Blink count (session total)
  - Blink rate (blinks per minute, rolling)
  - Long blink flag (closed for an unusually long run of frames -> possibly
    eyes shut / drowsiness / looking down at notes with eyes lowered)
  - Rapid blink flag (many blinks in a short window -> often correlates with
    stress/nervousness)
  - Fatigue score (0-100), combining blink rate deviation from the normal
    human baseline (~15-20/min) and long-blink frequency.
"""
from __future__ import annotations

import time
from collections import deque
from typing import Deque, Tuple

from models.schemas import BlinkMetrics

# Normal resting blink rate for an attentive adult is roughly 15-20 blinks/min.
NORMAL_BLINK_RATE_LOW = 12.0
NORMAL_BLINK_RATE_HIGH = 22.0


class BlinkAnalysisService:
    def __init__(self, ear_closed_threshold: float = 0.18, long_blink_frames: int = 8,
                 rapid_blink_window_s: float = 10.0, rapid_blink_count: int = 5) -> None:
        self.ear_closed_threshold = ear_closed_threshold
        self.long_blink_frames = long_blink_frames
        self.rapid_blink_window_s = rapid_blink_window_s
        self.rapid_blink_count = rapid_blink_count

        self._closed_frame_run = 0
        self._blink_count = 0
        self._blink_timestamps: Deque[float] = deque(maxlen=200)
        self._session_start = time.time()
        self._last_blink_was_long = False

    def analyze(self, avg_ear: float) -> BlinkMetrics:
        now = time.time()
        is_closed = avg_ear < self.ear_closed_threshold
        is_long_blink = False

        if is_closed:
            self._closed_frame_run += 1
        else:
            if self._closed_frame_run > 0:
                # Eyes just re-opened after being closed -> count as one blink
                self._blink_count += 1
                self._blink_timestamps.append(now)
                is_long_blink = self._closed_frame_run >= self.long_blink_frames
                self._last_blink_was_long = is_long_blink
            self._closed_frame_run = 0

        elapsed_min = max((now - self._session_start) / 60.0, 1e-6)
        blink_rate = self._blink_count / elapsed_min

        recent = [t for t in self._blink_timestamps if now - t <= self.rapid_blink_window_s]
        is_rapid_blink = len(recent) >= self.rapid_blink_count

        fatigue_score = self._compute_fatigue_score(blink_rate, is_long_blink)

        return BlinkMetrics(
            blink_count=self._blink_count,
            blink_rate_per_min=round(blink_rate, 1),
            is_long_blink=is_long_blink,
            is_rapid_blink=is_rapid_blink,
            fatigue_score=round(fatigue_score, 1),
        )

    def _compute_fatigue_score(self, blink_rate: float, is_long_blink: bool) -> float:
        if blink_rate < NORMAL_BLINK_RATE_LOW:
            rate_penalty = (NORMAL_BLINK_RATE_LOW - blink_rate) * 4.0  # very low rate -> staring/fatigue
        elif blink_rate > NORMAL_BLINK_RATE_HIGH:
            rate_penalty = (blink_rate - NORMAL_BLINK_RATE_HIGH) * 3.0  # very high rate -> eye strain
        else:
            rate_penalty = 0.0

        long_blink_penalty = 15.0 if is_long_blink else 0.0
        score = min(100.0, max(0.0, rate_penalty + long_blink_penalty))
        return score

    def reset(self) -> None:
        self._closed_frame_run = 0
        self._blink_count = 0
        self._blink_timestamps.clear()
        self._session_start = time.time()
