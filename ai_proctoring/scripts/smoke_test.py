"""
Standalone smoke test: exercises the entire proctoring pipeline in-process
(FaceMesh -> Pose -> feature extraction -> behavior scoring -> proctoring
engine -> report -> PDF) using synthetic frames, with NO webcam, NO
FastAPI server, and NO frontend involved. Useful as a fast first check that
your environment (Python version, dependencies, MediaPipe install) is
correctly set up before wiring up a real camera.

Run from the ai_proctoring/ directory:

    python scripts/smoke_test.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from models.schemas import SessionStatus
from services.report_generator import ReportGenerator
from services.session_manager import SessionPipeline


def main() -> None:
    print("Starting proctoring pipeline smoke test (synthetic frames)...\n")

    pipeline = SessionPipeline(
        session_id="smoke-test-session",
        interview_id="smoke-test-interview",
        user_id="smoke-test-user",
        candidate_name="Smoke Test Candidate",
    )

    for i in range(10):
        frame = (np.random.rand(480, 640, 3) * 255).astype("uint8")
        result = pipeline.process_frame(frame)
        warning_types = [w.type.value for w in result.warnings]
        print(
            f"frame {i:02d} | faces={result.face_quality.faces_detected} "
            f"| suspicious_score={result.suspicious_activity_score:5.1f} "
            f"| warnings={warning_types}"
        )

    pipeline.status = SessionStatus.COMPLETED
    report = pipeline.build_report()

    print("\n--- Session report ---")
    print(f"Overall score:      {report.overall_score}")
    print(f"Frames analyzed:    {report.frames_analyzed}")
    print(f"Suspicious events:  {report.suspicious_events_count}")
    print(f"Recruiter summary:  {report.recruiter_summary}")

    print("\nGenerating PDF report...")
    pdf_path = ReportGenerator().generate(report)
    print(f"PDF written to: {os.path.abspath(pdf_path)}")

    pipeline.close()
    print("\nSmoke test completed successfully — pipeline, scoring, and PDF generation all work.")
    print("Note: synthetic random-noise frames contain no real face, so 'faces=0' and")
    print("no_face_detected warnings above are EXPECTED, not a bug.")


if __name__ == "__main__":
    main()
