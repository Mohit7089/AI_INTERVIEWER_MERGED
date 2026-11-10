"""
Standalone webcam test client for the AI Proctoring service.

Talks to a RUNNING `ai_proctoring` FastAPI server (start it first with
`uvicorn main:app --port 8001`) using the exact same REST + WebSocket
protocol the React frontend uses -- so this is a faithful end-to-end test
of the whole service, just with an OpenCV window instead of a browser.

Usage:
    cd ai_proctoring
    pip install requests websocket-client   # test-only deps, not in requirements.txt
    python scripts/webcam_test_client.py

Controls:
    q  -  quit and finalize the session (generates the PDF report)
    f  -  simulate a "fullscreen exit" event (tests that warning path)

What it does:
    1. POST /api/proctoring/sessions/start  -> get session_id + ws url
    2. Opens your default webcam (index 0)
    3. Opens the WebSocket, streams JPEG frames a few times a second
    4. Draws the latest live scores + any active warnings directly on the
       video window
    5. On quit, POST /api/proctoring/sessions/{id}/end and prints the
       final report summary + where the PDF was saved
"""
from __future__ import annotations

import base64
import json
import sys
import threading
import time

import cv2
import requests

try:
    import websocket  # from the `websocket-client` package
except ImportError:
    print("Missing dependency. Install it with:\n    pip install websocket-client")
    sys.exit(1)

SERVICE_URL = "http://localhost:8001"
WS_URL = "ws://localhost:8001"
FRAMES_PER_SECOND = 3
JPEG_QUALITY = 70

latest_analysis: dict | None = None
active_warnings: list[dict] = []
ws_app: "websocket.WebSocketApp | None" = None
running = True


def on_message(ws, message: str) -> None:
    global latest_analysis, active_warnings
    payload = json.loads(message)
    if payload["type"] == "analysis":
        latest_analysis = payload["result"]
    elif payload["type"] == "warning":
        w = payload["warning"]
        active_warnings = [x for x in active_warnings if x["type"] != w["type"]] + [w]
        active_warnings = active_warnings[-5:]
        print(f"[WARNING] {w['severity'].upper():8s} {w['message']}")
    elif payload["type"] == "error":
        print(f"[SERVER ERROR] {payload['message']}")


def on_error(ws, error) -> None:
    print(f"[WS ERROR] {error}")


def on_close(ws, close_status_code, close_msg) -> None:
    print("[WS] connection closed")


def draw_overlay(frame, analysis: dict | None, warnings: list[dict]):
    y = 24
    if analysis:
        eye = analysis.get("eye", {})
        behavior = analysis.get("behavior", {})
        face_quality = analysis.get("face_quality", {})
        lines = [
            f"Faces: {face_quality.get('faces_detected', '?')}",
            f"Eye contact: {eye.get('eye_contact_score', 0):.0f}",
            f"Gaze: {eye.get('gaze_direction', '?')}",
            f"Attention: {behavior.get('attention', 0):.0f}",
            f"Confidence: {behavior.get('confidence', 0):.0f}",
            f"Stress: {behavior.get('stress', 0):.0f}",
            f"Suspicious score: {analysis.get('suspicious_activity_score', 0):.0f}",
        ]
        for line in lines:
            cv2.putText(frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1, cv2.LINE_AA)
            y += 22

    y += 10
    for w in warnings[-3:]:
        color = {"info": (255, 200, 0), "warning": (0, 200, 255), "critical": (0, 0, 255)}.get(
            w["severity"], (0, 0, 255)
        )
        cv2.putText(frame, w["message"][:60], (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
        y += 20

    return frame


def main() -> None:
    global ws_app, running

    print(f"Starting session against {SERVICE_URL} ...")
    resp = requests.post(
        f"{SERVICE_URL}/api/proctoring/sessions/start",
        json={"interview_id": "standalone-test", "user_id": "standalone-tester", "candidate_name": "Standalone Test"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    session_id = data["session_id"]
    ws_url = f"{WS_URL}{data['websocket_url']}"
    print(f"Session started: {session_id}")
    print(f"Connecting to {ws_url} ...")

    ws_app = websocket.WebSocketApp(ws_url, on_message=on_message, on_error=on_error, on_close=on_close)
    ws_thread = threading.Thread(target=ws_app.run_forever, daemon=True)
    ws_thread.start()
    time.sleep(1.0)  # give the socket a moment to connect

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Could not open webcam (index 0). Try a different index or check camera permissions.")
        return

    print("\nWebcam running. Press 'q' to quit and finalize, 'f' to simulate fullscreen exit.\n")

    frame_index = 0
    last_send = 0.0
    send_interval = 1.0 / FRAMES_PER_SECOND

    try:
        while running:
            ok, frame = cap.read()
            if not ok:
                break

            now = time.time()
            if now - last_send >= send_interval and ws_app.sock and ws_app.sock.connected:
                last_send = now
                frame_index += 1
                small = cv2.resize(frame, (480, int(frame.shape[0] * 480 / frame.shape[1])))
                ok, buf = cv2.imencode(".jpg", small, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
                if ok:
                    b64 = base64.b64encode(buf).decode("utf-8")
                    ws_app.send(json.dumps({
                        "type": "frame",
                        "image": f"data:image/jpeg;base64,{b64}",
                        "frame_index": frame_index,
                    }))

            display = draw_overlay(frame.copy(), latest_analysis, active_warnings)
            cv2.imshow("AI Proctoring - Standalone Test (q=quit, f=fullscreen-exit event)", display)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                running = False
            elif key == ord("f") and ws_app.sock and ws_app.sock.connected:
                ws_app.send(json.dumps({"type": "event", "event": "fullscreen_exit"}))
                print("[CLIENT] Sent simulated fullscreen_exit event")

    finally:
        cap.release()
        cv2.destroyAllWindows()
        if ws_app is not None:
            ws_app.close()

        print("\nFinalizing session...")
        end_resp = requests.post(f"{SERVICE_URL}/api/proctoring/sessions/{session_id}/end", timeout=30)
        if end_resp.status_code == 200:
            report = end_resp.json()
            print("\n--- Final report ---")
            print(f"Overall score:      {report['overall_score']}")
            print(f"Eye contact:        {report['eye_contact_percentage']}%")
            print(f"Attention:          {report['attention']}")
            print(f"Professionalism:    {report['professionalism']}")
            print(f"Suspicious events:  {report['suspicious_events_count']}")
            print(f"Recruiter summary:  {report['recruiter_summary']}")
            print(f"Candidate feedback: {report['candidate_feedback']}")
            if report.get("pdf_path"):
                print(f"PDF report saved at: {report['pdf_path']}")
        else:
            print(f"Could not finalize session: {end_resp.status_code} {end_resp.text}")


if __name__ == "__main__":
    main()
