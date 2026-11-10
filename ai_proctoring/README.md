# AI Interview Proctoring & Behavioral Analysis Service

A real-time, webcam-based proctoring and behavioral analytics engine for the
AI Interviewer platform. Runs as a **separate Python microservice**
alongside the existing Node/Express + React app, and talks to it over REST
+ WebSocket — no changes required to the existing backend.

## Architecture

```
Webcam (browser)
   │  JPEG frames over WebSocket
   ▼
FastAPI WebSocket endpoint  (api/ws_stream.py)
   ▼
SessionPipeline.process_frame()   (services/session_manager.py)
   │
   ├─ MediaPipe FaceMesh (478 landmarks + iris)  → FaceMeshService
   ├─ MediaPipe Pose                             → PoseService
   │
   ├─ EyeTrackingService      → EAR, iris gaze, eye-contact score
   ├─ HeadPoseService         → solvePnP pitch/yaw/roll, stability
   ├─ BlinkAnalysisService    → blink count/rate, fatigue score
   ├─ LipAnalysisService      → speaking, mouth open, compression, smile
   ├─ PostureAnalysisService  → leaning/slouching, professionalism score
   ├─ ReadingDetectionService → fixation/scan-pattern reading probability
   ├─ ObjectDetectionService  → optional YOLOv8 (phone/book/laptop)
   │
   ├─ BehaviorEngine     → confidence, calmness, nervousness, attention,
   │                        engagement, professionalism, stress
   ├─ ProctoringEngine   → debounced warnings + suspicious activity score
   │
   ▼
FrameAnalysisResult ──► sent back over WebSocket (live UI)
   │
   ▼ (aggregated over the session)
SessionReport ──► ReportGenerator (ReportLab + matplotlib) ──► PDF
                └► MongoDB (proctor_reports collection)
```

Every behavioral score is a documented, explainable function of measured
geometric features (EAR, gaze offsets, landmark variance, etc.) — there are
no random or black-box values anywhere in the scoring pipeline.

## Project structure

```
ai_proctoring/
├── main.py                  # FastAPI entrypoint
├── requirements.txt
├── .env.example
├── config/
│   └── settings.py          # typed, env-driven configuration
├── models/
│   ├── schemas.py           # Pydantic contracts (shared by CV/API/DB)
│   └── db_models.py         # Mongo document (de)serialization
├── services/
│   ├── face_mesh_service.py
│   ├── pose_service.py
│   ├── eye_tracking.py
│   ├── head_pose.py
│   ├── blink_analysis.py
│   ├── lip_analysis.py
│   ├── posture_analysis.py
│   ├── reading_detection.py
│   ├── object_detection.py  # optional YOLOv8, lazy-loaded
│   ├── behavior_engine.py
│   ├── proctoring_engine.py
│   ├── session_manager.py   # orchestrates the full per-session pipeline
│   └── report_generator.py  # PDF report (ReportLab + matplotlib)
├── db/
│   ├── mongo.py             # motor async connection
│   └── repository.py        # report persistence
├── api/
│   ├── routes_session.py    # start/end session REST endpoints
│   ├── routes_report.py     # PDF download + report history
│   └── ws_stream.py         # real-time WebSocket frame streaming
├── utils/
│   ├── geometry.py          # landmark index constants + vector math
│   ├── image_utils.py       # base64 <-> frame conversion
│   └── logger.py
├── tests/                   # unit tests (pure geometry/logic, no webcam needed)
├── reports/                 # generated PDFs land here
└── logs/
```

## Setup

```bash
cd ai_proctoring
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # adjust MONGO_URI etc. as needed
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Health check: `GET http://localhost:8001/health`

### Optional: object detection

Object detection (phone/book/laptop) is **off by default** to keep the base
install light and CPU-light. To enable it:

```bash
pip install ultralytics
# in .env:
ENABLE_OBJECT_DETECTION=true
YOLO_MODEL_PATH=yolov8n.pt   # auto-downloaded by ultralytics on first run
```

If the model can't be loaded (missing package, no internet, etc.), the
service logs a warning and continues running with object detection simply
disabled — it never takes down the rest of the pipeline.

## Running tests

```bash
cd ai_proctoring
pip install pytest
python3 -m pytest tests/ -v
```

All tests use synthetic, hand-constructed landmark data (see
`tests/fixtures.py`) — no webcam or real face image is required to validate
the algorithms.

## Testing the service completely standalone (no frontend, no Node backend)

The `ai_proctoring` service is fully independent — everything below needs
only this folder, and optionally MongoDB.

### 1. Synthetic smoke test (no webcam, fastest sanity check)

Exercises the full pipeline (FaceMesh → behavior scoring → proctoring →
report → PDF) with random synthetic frames, entirely in-process:

```bash
cd ai_proctoring
python scripts/smoke_test.py
```

`faces=0` / `no_face_detected` in the output is expected here — random
noise contains no real face. This just proves the pipeline wiring, scoring
math, and PDF generation all run without errors.

### 2. Real webcam test (no browser, no React needed)

Talks to a **running** instance of this service over the exact same REST +
WebSocket protocol the React frontend uses, but through an OpenCV window
instead of a browser:

```bash
# Terminal 1
cd ai_proctoring
uvicorn main:app --host 0.0.0.0 --port 8001

# Terminal 2
cd ai_proctoring
pip install -r scripts/requirements-test.txt
python scripts/webcam_test_client.py
```

A window opens showing your webcam feed with live eye contact / attention /
confidence / stress scores and any active warnings drawn directly on it.
Press `q` to end the session (generates the PDF in `reports/`), or `f` to
simulate a fullscreen-exit event.

### ⚠️ Important: always install exact pinned versions

Do **not** `pip install fastapi` / `pip install mediapipe` etc. without the
version pins in `requirements.txt`. Two real issues surfaced during
development from installing unpinned/latest versions instead of the pinned
ones:

- **mediapipe**: versions newer than `0.10.18` removed the legacy
  `mp.solutions` API (`FaceMesh`, `Pose`) that this service is built on, in
  favor of a new Tasks API. Installing latest mediapipe breaks
  `FaceMeshService`/`PoseService` at import time.
- **fastapi/starlette**: installing latest `fastapi` pulls in a much newer
  `starlette`, and that combination was observed to silently fail to
  register the WebSocket route (`/ws/proctoring/{session_id}`), returning a
  404 on every WebSocket connection attempt while REST endpoints kept
  working fine — a confusing failure mode if you don't know to check
  package versions first.

Always run `pip install -r requirements.txt` (which respects the pins) as
a single command, rather than installing packages individually.


| Method | Path | Description |
|---|---|---|
| POST | `/api/proctoring/sessions/start` | Start a session → `{session_id, websocket_url}` |
| POST | `/api/proctoring/sessions/{id}/end` | Finalize a session → full `SessionReport` (also generates + persists PDF) |
| GET | `/api/proctoring/sessions/{id}/report` | Fetch a persisted report by session id |
| GET | `/api/proctoring/sessions/by-interview/{interview_id}` | Fetch the latest report for an interview |
| GET | `/api/proctoring/reports/{id}/pdf` | Download the generated PDF |
| GET | `/api/proctoring/reports/user/{user_id}` | List a candidate's report history |

## WebSocket protocol

`ws://<host>:8001/ws/proctoring/{session_id}`

Client → Server:
```json
{"type": "frame", "image": "data:image/jpeg;base64,...", "frame_index": 42}
{"type": "event", "event": "fullscreen_exit"}
```

Server → Client:
```json
{"type": "analysis", "result": { ...FrameAnalysisResult... }}
{"type": "warning",  "warning": { "type": "looking_away", "severity": "warning", "message": "..." }}
```

## Frontend integration (client/)

Two new files were added under `client/src/`, entirely additive — no
existing files were modified:

- `client/src/config/proctoringConfig.js` — base URL of this service.
- `client/src/hooks/useProctoring.js` — manages webcam capture, the
  WebSocket connection, and session start/end lifecycle.
- `client/src/components/ProctoringPanel.jsx` — a drop-in floating panel
  (webcam preview + live scores + warning banner).

To wire it into the live interview screen, add to `Step2Interview.jsx`:

```jsx
import ProctoringPanel from './ProctoringPanel'
import { useSelector } from 'react-redux'

// inside the component:
const userData = useSelector((state) => state.user.userData)

// inside the JSX, alongside the existing interview UI:
<ProctoringPanel
  interviewId={interviewId}
  userId={userData?._id}
  candidateName={userName}
  active={!isIntroPhase}   // starts monitoring once the interview begins
  onReportReady={(report) => console.log('Proctoring report:', report)}
/>
```

`onReportReady` fires once the session ends (e.g. when the interview
finishes) with the full `SessionReport`, including the `pdf_path` you can
turn into a download link via `GET /api/proctoring/reports/{id}/pdf`.

## Notes on scaling & production hardening

- `SessionManager` currently keeps sessions in an in-memory dict — fine for
  a single-process deployment. For horizontal scaling, back it with a
  shared store (Redis) keyed by `session_id` and use sticky routing/session
  affinity at the load balancer for WebSocket connections.
- MongoDB writes are best-effort: if Mongo is unreachable, the service logs
  a warning and keeps running (PDF generation, live analysis, and warnings
  all continue to work); only persistence of the final report is affected.
- Object detection is intentionally decoupled and optional so the core
  face/behavior pipeline never depends on a heavy YOLO install.
