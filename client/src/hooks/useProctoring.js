import { useCallback, useEffect, useRef, useState } from "react";
import {
  ProctoringServerUrl,
  ProctoringWsOrigin,
  PROCTORING_FRAME_INTERVAL_MS,
} from "../config/proctoringConfig.js";

/**
 * Manages the full lifecycle of a proctoring session against the
 * ai_proctoring FastAPI microservice:
 *   1. Ask for webcam access
 *   2. POST /api/proctoring/sessions/start
 *   3. Open the WebSocket and stream JPEG frames
 *   4. Receive live FrameAnalysisResult / WarningEvent messages
 *   5. POST /api/proctoring/sessions/{id}/end when `active` turns false
 *
 * The proctoring service is intentionally best-effort: any failure here
 * (camera denied, service offline, network error) is captured in `error`
 * and never throws, so the interview itself always keeps working.
 */
export function useProctoring({
  interviewId,
  userId,
  candidateName,
  active,
  onReportReady,
}) {
  const [status, setStatus] = useState("idle"); // idle | connecting | active | ending | ended | error
  const [isConnected, setIsConnected] = useState(false);
  const [latestResult, setLatestResult] = useState(null);
  const [activeWarning, setActiveWarning] = useState(null);
  const [warningLog, setWarningLog] = useState([]);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const wsRef = useRef(null);
  const sessionIdRef = useRef(null);
  const frameIndexRef = useRef(0);
  const frameTimerRef = useRef(null);
  const warningTimerRef = useRef(null);
  const startedRef = useRef(false);

  const captureFrame = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState < 2) return null;

    const targetWidth = 480;
    const scale = targetWidth / video.videoWidth;
    canvas.width = targetWidth;
    canvas.height = video.videoHeight * scale || 360;

    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.6);
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  }, []);

  const stopStreaming = useCallback(() => {
    if (frameTimerRef.current) {
      clearInterval(frameTimerRef.current);
      frameTimerRef.current = null;
    }
    if (wsRef.current) {
      try {
        wsRef.current.close();
      } catch {
        /* noop */
      }
      wsRef.current = null;
    }
  }, []);

  const endSession = useCallback(async () => {
    stopStreaming();
    stopCamera();

    const sessionId = sessionIdRef.current;
    if (!sessionId) {
      setStatus("ended");
      return;
    }

    setStatus("ending");
    try {
      const res = await fetch(
        `${ProctoringServerUrl}/api/proctoring/sessions/${sessionId}/end`,
        { method: "POST" }
      );
      if (res.ok) {
        const data = await res.json();
        setReport(data);
        onReportReady?.(data);
      }
    } catch (err) {
      setError(err.message || "Failed to finalize proctoring session");
    } finally {
      sessionIdRef.current = null;
      startedRef.current = false;
      setIsConnected(false);
      setStatus("ended");
    }
  }, [onReportReady, stopCamera, stopStreaming]);

  const startSession = useCallback(async () => {
    if (startedRef.current) return;
    startedRef.current = true;
    setStatus("connecting");
    setError(null);

    try {
      // 1. Webcam
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 480, height: 360 },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {});
      }

      // 2. Start session
      const startRes = await fetch(
        `${ProctoringServerUrl}/api/proctoring/sessions/start`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            interview_id: interviewId,
            user_id: userId,
            candidate_name: candidateName,
          }),
        }
      );
      if (!startRes.ok) throw new Error("Could not start proctoring session");
      const { session_id, websocket_url } = await startRes.json();
      sessionIdRef.current = session_id;

      // 3. WebSocket
      const ws = new WebSocket(`${ProctoringWsOrigin}${websocket_url}`);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setStatus("active");
        frameTimerRef.current = setInterval(() => {
          const image = captureFrame();
          if (image && ws.readyState === WebSocket.OPEN) {
            ws.send(
              JSON.stringify({
                type: "frame",
                image,
                frame_index: frameIndexRef.current++,
              })
            );
          }
        }, PROCTORING_FRAME_INTERVAL_MS);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "analysis") {
            setLatestResult(msg.result);
          } else if (msg.type === "warning") {
            setActiveWarning(msg.warning);
            setWarningLog((prev) => [msg.warning, ...prev].slice(0, 20));
            if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
            warningTimerRef.current = setTimeout(
              () => setActiveWarning(null),
              5000
            );
          }
        } catch {
          /* ignore malformed message */
        }
      };

      ws.onerror = () => {
        setError("Proctoring connection lost");
      };

      ws.onclose = () => {
        setIsConnected(false);
      };
    } catch (err) {
      setError(err.message || "Proctoring unavailable");
      setStatus("error");
      startedRef.current = false;
    }
  }, [candidateName, captureFrame, interviewId, userId]);

  // Drive the lifecycle off the `active` flag.
  useEffect(() => {
    if (active && !startedRef.current) {
      startSession();
    } else if (!active && startedRef.current) {
      endSession();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  // Always clean up on unmount.
  useEffect(() => {
    return () => {
      stopStreaming();
      stopCamera();
      if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
    };
  }, [stopStreaming, stopCamera]);

  const sendEvent = useCallback((eventName) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "event", event: eventName }));
    }
  }, []);

  return {
    videoRef,
    canvasRef,
    status,
    isConnected,
    latestResult,
    activeWarning,
    warningLog,
    report,
    error,
    sendEvent,
    endSession,
  };
}
