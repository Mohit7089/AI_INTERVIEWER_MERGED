"""
Geometry primitives and MediaPipe FaceMesh landmark index constants.

MediaPipe FaceMesh (with `refine_landmarks=True`) outputs 478 3D landmarks:
  - Indices 0-467   : the standard face mesh (eyes, brows, nose, lips, jaw, chin, forehead, cheeks)
  - Indices 468-477 : refined iris landmarks (5 per eye)

All index sets below are the well-established indices used throughout the
MediaPipe community for eye/iris/mouth/eyebrow work.
"""
from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

import numpy as np

Point = Tuple[float, float]
Point3D = Tuple[float, float, float]

# ---------------------------------------------------------------------------
# Landmark index groups
# ---------------------------------------------------------------------------

# Eye Aspect Ratio (EAR) landmark sets: [left corner, top1, top2, right corner, bottom2, bottom1]
LEFT_EYE_EAR = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_EAR = [362, 385, 387, 263, 373, 380]

# Full eye contour (for bounding box / crop)
LEFT_EYE_CONTOUR = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
RIGHT_EYE_CONTOUR = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]

# Iris landmarks (only present when refine_landmarks=True)
LEFT_IRIS = [468, 469, 470, 471, 472]
RIGHT_IRIS = [473, 474, 475, 476, 477]

# Eyebrows
LEFT_EYEBROW = [70, 63, 105, 66, 107, 55, 65]
RIGHT_EYEBROW = [300, 293, 334, 296, 336, 285, 295]

# Mouth / lips
OUTER_LIPS = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]
INNER_LIPS = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191]
MOUTH_LEFT_CORNER = 61
MOUTH_RIGHT_CORNER = 291
UPPER_LIP_TOP = 13
LOWER_LIP_BOTTOM = 14
UPPER_LIP_OUTER = 0
LOWER_LIP_OUTER = 17

# Nose
NOSE_TIP = 1
NOSE_BRIDGE = 168

# Jaw / chin / forehead
CHIN = 152
JAWLINE = [162, 21, 54, 58, 172, 136, 150, 149, 176, 148, 152, 377, 400, 378, 379, 365, 397, 288, 361, 323, 389]
FOREHEAD = 10  # approx top of forehead / hairline landmark

# 6-point set used for solvePnP head-pose estimation (2D image points correspond
# to a canonical 3D face model defined in head_pose.py)
HEAD_POSE_LANDMARKS = {
    "nose_tip": 1,
    "chin": 152,
    "left_eye_left_corner": 33,
    "right_eye_right_corner": 263,
    "mouth_left_corner": 61,
    "mouth_right_corner": 291,
}

FACE_OVAL = [
    10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379,
    378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127,
    162, 21, 54, 103, 67, 109,
]


# ---------------------------------------------------------------------------
# Vector / geometry helpers
# ---------------------------------------------------------------------------

def euclidean_distance(p1: Sequence[float], p2: Sequence[float]) -> float:
    """Euclidean distance between two 2D or 3D points."""
    return float(math.dist(p1, p2))


def midpoint(p1: Sequence[float], p2: Sequence[float]) -> Point:
    return ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)


def landmarks_to_pixel_coords(
    landmarks, frame_width: int, frame_height: int
) -> List[Point3D]:
    """
    Convert normalized MediaPipe landmarks (x, y, z in [0,1]) into pixel-space
    coordinates. z is kept relative (roughly in the same scale as x after
    multiplying by width, per MediaPipe convention).
    """
    return [
        (lm.x * frame_width, lm.y * frame_height, lm.z * frame_width)
        for lm in landmarks
    ]


def get_points(coords: Sequence[Point3D], indices: Iterable[int]) -> List[Point3D]:
    """Select a subset of pixel-space coordinates by landmark index."""
    return [coords[i] for i in indices]


def polygon_centroid(points: Sequence[Sequence[float]]) -> Point:
    arr = np.asarray(points, dtype=np.float64)
    return float(np.mean(arr[:, 0])), float(np.mean(arr[:, 1]))


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def normalize_score(value: float, low: float, high: float) -> float:
    """Linearly map `value` in [low, high] to a 0-100 score, clamped."""
    if high == low:
        return 0.0
    pct = (value - low) / (high - low) * 100.0
    return clamp(pct, 0.0, 100.0)


def moving_average(values: Sequence[float], window: int) -> float:
    if not values:
        return 0.0
    window = min(window, len(values))
    return float(np.mean(values[-window:]))


def bounding_box(points: Sequence[Sequence[float]]) -> Tuple[float, float, float, float]:
    """Return (x_min, y_min, x_max, y_max) for a set of 2D/3D points."""
    arr = np.asarray(points, dtype=np.float64)
    return (
        float(np.min(arr[:, 0])),
        float(np.min(arr[:, 1])),
        float(np.max(arr[:, 0])),
        float(np.max(arr[:, 1])),
    )
