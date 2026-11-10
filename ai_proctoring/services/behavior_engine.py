"""
BehaviorEngine

Combines the outputs of every low-level analysis module (eye, head pose,
blink, lip, posture, reading) into higher-level, explainable behavioral
scores: confidence, calmness, nervousness, attention, engagement,
professionalism, and stress.

Every score is a documented weighted function of concrete measured features
-- never a random or opaque value -- so a recruiter (or the candidate) can
trust and, if needed, audit why a score landed where it did.
"""
from __future__ import annotations

from models.schemas import (
    BehaviorScores,
    BlinkMetrics,
    EyeMetrics,
    HeadPoseMetrics,
    LipMetrics,
    PostureMetrics,
    ReadingMetrics,
)
from utils.geometry import clamp


class BehaviorEngine:
    """Stateless combiner -- takes one frame's worth of metrics, returns scores.

    Smoothing across frames happens upstream via each metric's own rolling
    windows (eye contact score, head stability, blink rate, etc.), so this
    engine can stay a pure function of "current metrics" without keeping its
    own history.
    """

    def score(
        self,
        eye: EyeMetrics,
        head_pose: HeadPoseMetrics,
        blink: BlinkMetrics,
        lip: LipMetrics,
        posture: PostureMetrics,
        reading: ReadingMetrics,
    ) -> BehaviorScores:
        attention = self._attention(eye, reading)
        engagement = self._engagement(eye, lip, attention)
        stress = self._stress(blink, head_pose, lip, posture)
        calmness = clamp(100.0 - stress, 0.0, 100.0)
        nervousness = self._nervousness(blink, lip, head_pose, stress)
        professionalism = self._professionalism(posture, head_pose)
        confidence = self._confidence(eye, posture, head_pose, nervousness)

        return BehaviorScores(
            confidence=round(confidence, 1),
            calmness=round(calmness, 1),
            nervousness=round(nervousness, 1),
            attention=round(attention, 1),
            engagement=round(engagement, 1),
            professionalism=round(professionalism, 1),
            stress=round(stress, 1),
        )

    # -- Individual score functions -----------------------------------------

    @staticmethod
    def _attention(eye: EyeMetrics, reading: ReadingMetrics) -> float:
        # High eye contact + low reading probability = strong attention signal
        score = 0.75 * eye.eye_contact_score + 0.25 * (100.0 - reading.reading_probability)
        return clamp(score, 0.0, 100.0)

    @staticmethod
    def _engagement(eye: EyeMetrics, lip: LipMetrics, attention: float) -> float:
        speaking_bonus = 8.0 if lip.is_speaking else 0.0
        score = 0.7 * attention + 0.3 * eye.eye_contact_score + speaking_bonus
        return clamp(score, 0.0, 100.0)

    @staticmethod
    def _stress(blink: BlinkMetrics, head_pose: HeadPoseMetrics, lip: LipMetrics,
                posture: PostureMetrics) -> float:
        rapid_blink_penalty = 25.0 if blink.is_rapid_blink else 0.0
        instability_penalty = (100.0 - head_pose.stability_score) * 0.35
        compression_penalty = lip.lip_compression * 25.0
        posture_penalty = (100.0 - posture.professionalism_score) * 0.15
        score = rapid_blink_penalty + instability_penalty + compression_penalty + posture_penalty
        return clamp(score, 0.0, 100.0)

    @staticmethod
    def _nervousness(blink: BlinkMetrics, lip: LipMetrics, head_pose: HeadPoseMetrics,
                      stress: float) -> float:
        fidget_penalty = (100.0 - head_pose.stability_score) * 0.3
        blink_penalty = 15.0 if (blink.is_rapid_blink or blink.blink_rate_per_min > 25) else 0.0
        compression_penalty = lip.lip_compression * 20.0
        score = 0.5 * stress + fidget_penalty * 0.3 + blink_penalty + compression_penalty * 0.2
        return clamp(score, 0.0, 100.0)

    @staticmethod
    def _professionalism(posture: PostureMetrics, head_pose: HeadPoseMetrics) -> float:
        score = 0.7 * posture.professionalism_score + 0.3 * head_pose.stability_score
        return clamp(score, 0.0, 100.0)

    @staticmethod
    def _confidence(eye: EyeMetrics, posture: PostureMetrics, head_pose: HeadPoseMetrics,
                     nervousness: float) -> float:
        score = (
            0.4 * eye.eye_contact_score
            + 0.25 * posture.professionalism_score
            + 0.2 * head_pose.stability_score
            + 0.15 * (100.0 - nervousness)
        )
        return clamp(score, 0.0, 100.0)
