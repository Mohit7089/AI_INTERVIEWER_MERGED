// Base URL of the ai_proctoring FastAPI microservice.
// Override by setting VITE_PROCTORING_URL in client/.env if it runs elsewhere.
export const ProctoringServerUrl =
  import.meta.env.VITE_PROCTORING_URL || "http://localhost:8001";

// Derive the ws:// or wss:// origin from ProctoringServerUrl automatically.
export const ProctoringWsOrigin = ProctoringServerUrl.replace(/^http/, "ws");

// How often (ms) we capture + send a webcam frame over the WebSocket.
export const PROCTORING_FRAME_INTERVAL_MS = 1000;
