"""
Synthetic landmark generators used across unit tests, so tests don't depend
on a real webcam/MediaPipe model at all -- they exercise pure geometry and
scoring logic against known, hand-placed coordinates.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

Point3D = Tuple[float, float, float]

NUM_LANDMARKS = 478


def make_face_landmarks(overrides: Dict[int, Point3D]) -> List[Point3D]:
    """Return a 478-point landmark list, all defaulting to (0,0,0) except the
    given index -> (x,y,z) overrides. Sufficient for testing any module that
    only reads a known subset of indices (EAR, iris, mouth, head-pose, etc.)."""
    landmarks: List[Point3D] = [(0.0, 0.0, 0.0)] * NUM_LANDMARKS
    for idx, point in overrides.items():
        landmarks[idx] = point
    return landmarks


def frontal_face_landmarks(eyes_open: bool = True) -> List[Point3D]:
    """
    A geometrically-consistent, truly-frontal synthetic face (image space,
    y-down), sized for a 640x480 frame.

    The 6 head-pose landmarks (nose tip, chin, eye corners, mouth corners)
    are derived by projecting the *same* canonical 3D face model used by
    HeadPoseService (see services/head_pose.py:_MODEL_POINTS_3D) with zero
    rotation, so a truly frontal face is guaranteed to yield pitch/yaw/roll
    close to zero. All other fine-grained points (EAR sub-points, iris,
    inner mouth) are then placed relative to those anchors.
    """
    import numpy as np

    w, h = 640, 480
    focal = w
    cam = np.array([[focal, 0, w / 2], [0, focal, h / 2], [0, 0, 1]], dtype=np.float64)

    # Same 3D model points/order as services/head_pose.py::_MODEL_POINTS_3D
    model_points_3d = np.array([
        (0.0, 0.0, 0.0),          # nose_tip
        (0.0, -63.6, -12.5),      # chin
        (-43.3, 32.7, -26.0),     # left_eye_left_corner
        (43.3, 32.7, -26.0),      # right_eye_right_corner
        (-28.9, -28.9, -24.1),    # mouth_left_corner
        (28.9, -28.9, -24.1),     # mouth_right_corner
    ], dtype=np.float64)

    translation = np.array([0.0, 0.0, 500.0])  # camera looking straight at the face
    projected = []
    for point in model_points_3d:
        cam_pt = point + translation  # identity rotation
        proj = cam @ cam_pt
        proj = proj / proj[2]
        projected.append((float(proj[0]), float(proj[1])))

    nose_tip, chin, left_eye_l, right_eye_r, mouth_l, mouth_r = projected

    eye_gap = 6.0 if eyes_open else 1.0
    left_eye_center_x = left_eye_l[0] + 12.0
    left_eye_y = left_eye_l[1]
    right_eye_center_x = right_eye_r[0] - 12.0
    right_eye_y = right_eye_r[1]

    overrides: Dict[int, Point3D] = {
        # --- Left eye EAR points: [corner_l, top1, top2, corner_r, bottom2, bottom1]
        33: (left_eye_l[0], left_eye_y, 0.0),
        160: (left_eye_center_x - 4, left_eye_y - eye_gap, 0.0),
        158: (left_eye_center_x + 4, left_eye_y - eye_gap, 0.0),
        133: (left_eye_l[0] + 24.0, left_eye_y, 0.0),
        153: (left_eye_center_x + 4, left_eye_y + eye_gap, 0.0),
        144: (left_eye_center_x - 4, left_eye_y + eye_gap, 0.0),
        # --- Right eye EAR points
        362: (right_eye_r[0] - 24.0, right_eye_y, 0.0),
        385: (right_eye_center_x - 4, right_eye_y - eye_gap, 0.0),
        387: (right_eye_center_x + 4, right_eye_y - eye_gap, 0.0),
        263: (right_eye_r[0], right_eye_y, 0.0),
        373: (right_eye_center_x + 4, right_eye_y + eye_gap, 0.0),
        380: (right_eye_center_x - 4, right_eye_y + eye_gap, 0.0),
        # --- Iris centers (centered within each eye => "looking at camera")
        468: (left_eye_center_x - 2, left_eye_y, 0.0), 469: (left_eye_center_x, left_eye_y, 0.0),
        470: (left_eye_center_x, left_eye_y - 2, 0.0), 471: (left_eye_center_x + 2, left_eye_y, 0.0),
        472: (left_eye_center_x, left_eye_y + 2, 0.0),
        473: (right_eye_center_x - 2, right_eye_y, 0.0), 474: (right_eye_center_x, right_eye_y, 0.0),
        475: (right_eye_center_x, right_eye_y - 2, 0.0), 476: (right_eye_center_x + 2, right_eye_y, 0.0),
        477: (right_eye_center_x, right_eye_y + 2, 0.0),
        # --- Mouth
        61: (mouth_l[0], mouth_l[1], 0.0), 291: (mouth_r[0], mouth_r[1], 0.0),
        13: (320.0, mouth_l[1] - 4, 0.0), 14: (320.0, mouth_l[1] + 4, 0.0),
        0: (320.0, mouth_l[1] - 8, 0.0), 17: (320.0, mouth_l[1] + 8, 0.0),
        # --- Head pose 6-point set
        1: (nose_tip[0], nose_tip[1], 0.0),
        152: (chin[0], chin[1], 0.0),
    }
    return make_face_landmarks(overrides)
