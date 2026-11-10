"""
ReadingDetectionService

Detects whether the candidate is likely reading from a second monitor,
paper, or notes -- rather than thinking/speaking naturally -- by looking for
the characteristic eye-movement signature of reading:

  - Fixation: brief pauses in gaze (low velocity) interspersed with...
  - Horizontal scan: repeated left-to-right (or right-to-left) gaze sweeps,
    the hallmark of scanning lines of text.
  - Vertical scan: periodic downward gaze steps between horizontal sweeps
    (moving to the next line), often paired with small saccades back to the
    left margin.
  - Gaze oscillation: a rhythmic, low-amplitude, high-frequency component in
    the horizontal gaze signal (distinct from the smoother movements of
    naturally recalling an answer).
  - Head pose correlation: a downward/sideways pitch or yaw held steady while
    the above gaze pattern occurs (looking down at a phone/notes, or
    sideways at a second screen) strengthens the signal.

All signals are combined into a 0-100 Reading Probability using weighted,
explainable heuristics over a rolling window -- no black-box model.
"""
from __future__ import annotations

from collections import deque
from typing import Deque, Tuple

import numpy as np

from models.schemas import ReadingMetrics


class ReadingDetectionService:
    def __init__(self, window_size: int = 45) -> None:
        self._gaze_x_history: Deque[float] = deque(maxlen=window_size)
        self._gaze_y_history: Deque[float] = deque(maxlen=window_size)
        self._yaw_history: Deque[float] = deque(maxlen=window_size)
        self._pitch_history: Deque[float] = deque(maxlen=window_size)

    def analyze(self, gaze_x: float, gaze_y: float, yaw: float, pitch: float) -> ReadingMetrics:
        self._gaze_x_history.append(gaze_x)
        self._gaze_y_history.append(gaze_y)
        self._yaw_history.append(yaw)
        self._pitch_history.append(pitch)

        if len(self._gaze_x_history) < max(10, self._gaze_x_history.maxlen // 3):
            return ReadingMetrics()

        gx = np.array(self._gaze_x_history)
        gy = np.array(self._gaze_y_history)

        # --- Fixation: consecutive frames with very small gaze velocity ---
        velocity = np.abs(np.diff(gx)) + np.abs(np.diff(gy))
        fixation_frames = np.sum(velocity < 0.03)
        fixation_ratio = fixation_frames / max(1, len(velocity))
        fixation_detected = bool(fixation_ratio > 0.35)

        # --- Horizontal scan: zero-crossing rate of horizontal gaze velocity,
        #     i.e. how often the eyes reverse direction left<->right, which
        #     spikes during line-by-line reading. ---
        gx_velocity = np.diff(gx)
        sign_changes = np.sum(np.diff(np.sign(gx_velocity)) != 0)
        horizontal_scan_score = sign_changes / max(1, len(gx_velocity))
        horizontal_scan_detected = bool(horizontal_scan_score > 0.25 and np.std(gx) > 0.08)

        # --- Vertical scan: periodic small downward steps in vertical gaze
        #     (line breaks), detected as a net-positive drift with saccades. ---
        gy_diffs = np.diff(gy)
        downward_steps = np.sum(gy_diffs > 0.04)
        vertical_scan_detected = bool(downward_steps >= 3)

        # --- Gaze oscillation: FFT-free proxy via variance of short-lag
        #     differences relative to overall variance (high-frequency energy). ---
        short_lag_var = float(np.var(gx_velocity)) if len(gx_velocity) else 0.0
        overall_var = float(np.var(gx)) + 1e-6
        oscillation_ratio = short_lag_var / overall_var

        # --- Head pose correlation: steady downward pitch or repeated yaw
        #     shifts (second monitor) strengthen the reading hypothesis. ---
        pitch_arr = np.array(self._pitch_history)
        yaw_arr = np.array(self._yaw_history)
        steady_downward_pitch = bool(np.mean(pitch_arr) < -8.0 and np.std(pitch_arr) < 6.0)
        repeated_yaw_shift = bool(np.std(yaw_arr) > 6.0 and np.mean(np.abs(yaw_arr)) > 10.0)

        # --- Weighted combination into a 0-100 probability ---
        score = 0.0
        score += 25.0 if fixation_detected else 0.0
        score += 30.0 if horizontal_scan_detected else 0.0
        score += 15.0 if vertical_scan_detected else 0.0
        score += min(15.0, oscillation_ratio * 30.0)
        score += 10.0 if steady_downward_pitch else 0.0
        score += 5.0 if repeated_yaw_shift else 0.0
        reading_probability = float(np.clip(score, 0.0, 100.0))

        return ReadingMetrics(
            reading_probability=round(reading_probability, 1),
            horizontal_scan_detected=horizontal_scan_detected,
            vertical_scan_detected=vertical_scan_detected,
            fixation_detected=fixation_detected,
        )

    def reset(self) -> None:
        self._gaze_x_history.clear()
        self._gaze_y_history.clear()
        self._yaw_history.clear()
        self._pitch_history.clear()
