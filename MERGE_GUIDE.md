# Merging `ai_proctoring` into `AI_INTERVIEWER`

`ai_proctoring` was already designed to be a **separate microservice** that
talks to the existing Node/React app over REST + WebSocket — it doesn't
require any changes to `server/`. What was missing was the three frontend
files its own README describes (they were documented but not actually in
the zip), and the wiring into `Step2Interview.jsx`. Both are done in this
merged copy. Here's exactly what changed and what you need to configure.

## What was added / changed

```
AI_INTERVIEWER/
├── ai_proctoring/                        # ← whole service copied in, untouched
│   └── .env                              # ← created from .env.example
├── client/src/
│   ├── config/proctoringConfig.js        # ← new: proctoring service base URL
│   ├── hooks/useProctoring.js            # ← new: webcam + WS + session lifecycle
│   └── components/
│       ├── ProctoringPanel.jsx           # ← new: floating live panel
│       └── Step2Interview.jsx            # ← edited: renders <ProctoringPanel/>
└── package.json                          # ← edited: added "proctoring" script
```

`Step2Interview.jsx` now pulls `userData` from Redux and renders:

```jsx
<ProctoringPanel
  interviewId={interviewId}
  userId={userData?._id}
  candidateName={userName}
  active={!isIntroPhase}   // starts monitoring once the interview begins
  onReportReady={(report) => console.log('Proctoring report:', report)}
/>
```

Nothing else in `client/` or `server/` was touched.

## Why this works without backend changes

- The proctoring service's default CORS list (`ai_proctoring/config/settings.py`)
  already allows `http://localhost:5173`, so the Vite dev client can call it
  directly — no proxy needed.
- It listens on port **8001** by default, separate from the Express API
  (port 4000/8000 — see the port mismatch note below) and Vite (5173), so
  nothing collides.
- It writes proctoring reports to its **own** MongoDB collections
  (`proctor_reports`) in the same database your Express app already uses,
  keyed by `interview_id`/`user_id` — no schema changes to your existing
  Mongoose models are required to run it.

## Setup steps

### 1. Install the new service's dependencies

```bash
cd ai_proctoring
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

⚠️ Use a **Python 3.10 or 3.11** environment for this venv specifically.
`mediapipe==0.10.18` (pinned deliberately — see `ai_proctoring/README.md`)
does not support Python 3.12+. This can be a different Python version than
whatever you use for `resume-analyzer-api`.

### 2. Configure `ai_proctoring/.env`

Already created for you from `.env.example` with sane local defaults:

```env
PORT=8001
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:4000
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=ai_interviewer
```

Point `MONGO_URI`/`MONGO_DB_NAME` at the same MongoDB instance your
`server/.env` uses if you want proctoring reports and interview data in one
place (they land in a separate collection either way, so this is optional).

### 3. Fix the pre-existing `server/.env` mismatch (unrelated to proctoring, but blocks everything if you don't do it)

The client (`client/src/App.jsx`) hardcodes:

```js
export const ServerUrl = "http://localhost:8000"
```

but `server/index.js` and `server/config/connectDb.js` / `middlewares/isAuth.js`
actually read `process.env.PORT`, `process.env.MONGODB_URL`, and
`process.env.JWTSECRET` — **not** the `PORT`/`MONGODB_URI`/`JWT_SECRET`
names used in the original `SETUP.md`. Use these exact names in
`server/.env`:

```env
PORT=8000
MONGODB_URL=YOUR_MONGODB_CONNECTION_STRING
JWTSECRET=YOUR_JWT_SECRET
OPENROUTER_API_KEY=YOUR_OPENROUTER_API_KEY
CLIENT_URL=http://localhost:5173
```

### 4. Install everything else as usual

```bash
npm install               # root
cd client && npm install
cd ../server && npm install
cd ../resume-analyzer-api && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
```

### 5. Run all four services together

```bash
npm run dev
```

This now starts, via `concurrently`: React client (5173), Express server
(8000), Flask resume analyzer, and the FastAPI proctoring service (8001).

Or run proctoring on its own for testing:

```bash
cd ai_proctoring
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Health check: `GET http://localhost:8001/health`

## How it behaves at runtime

1. `Step1SetUp` → `Step2Interview` mounts; `ProctoringPanel` sits fixed in
   the bottom-right corner.
2. Once the AI's intro finishes (`isIntroPhase` becomes `false`), the panel
   asks for webcam permission, opens a session on the proctoring service,
   and starts streaming frames over WebSocket — independent of the
   speech-recognition/answer flow already in `Step2Interview.jsx`.
3. Live behavior scores (attention, confidence, engagement, calmness) and a
   suspicious-activity percentage update in the panel; warnings (e.g.
   looking away, fullscreen exit) show as a toast for a few seconds.
4. When the interview finishes and `active` flips back to `false`, the
   panel ends the session, the service generates a PDF report, and
   `onReportReady(report)` fires with the full `SessionReport` (currently
   just logged to the console — hook it into `Step3Report.jsx` or your
   report page if you want to surface it to the user, e.g. a download link
   via `GET /api/proctoring/reports/{id}/pdf`).

If the proctoring service is offline or the user denies camera access, the
panel shows a small "unavailable" state and the interview continues
normally — it never blocks the core flow.

## Optional next step: surface the report in Step3Report / InterviewReport

Right now the finished `SessionReport` only goes to `onReportReady`. If you
want it visible to the user, you can fetch it directly by interview id from
`Step3Report.jsx` or `InterviewReport.jsx`:

```js
const proctorReport = await fetch(
  `http://localhost:8001/api/proctoring/sessions/by-interview/${interviewId}`
).then(r => r.json());
```

and link `proctorReport.pdf_path` via
`GET http://localhost:8001/api/proctoring/reports/{proctorReport.session_id}/pdf`.
This wasn't added automatically since it touches your report UI/design.
