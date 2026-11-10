import React, { useState } from "react";
import { BsShieldCheck, BsExclamationTriangle } from "react-icons/bs";

/**
 * Drop-in floating proctoring panel. Wire it into the live interview screen:
 *
 *   <ProctoringPanel
 *     interviewId={interviewId}
 *     userId={userData?._id}
 *     candidateName={userName}
 *     active={!isIntroPhase}
 *     onReportReady={(report) => console.log(report)}
 *   />
 *
 * It is entirely self-contained: if the ai_proctoring service is offline or
 * the user denies camera access, it fails quietly (shows a small notice)
 * and never blocks the interview flow.
 */
function ProctoringPanel({ videoRef, canvasRef, status, isConnected, latestResult, activeWarning, error }) {
  const [minimized, setMinimized] = useState(false);

  const behavior = latestResult?.behavior;
  const suspicious = latestResult?.suspicious_activity_score ?? 0;

  return (
    <div className="fixed bottom-4 right-4 z-50 w-64 sm:w-72 font-sans">
      {activeWarning && (
        <div className="mb-2 flex items-start gap-2 rounded-xl border border-amber-300 bg-amber-50 p-3 shadow-lg animate-pulse">
          <BsExclamationTriangle className="mt-0.5 shrink-0 text-amber-600" />
          <p className="text-xs font-medium text-amber-800">{activeWarning.message}</p>
        </div>
      )}

      <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-2xl">
        <button
          onClick={() => setMinimized((m) => !m)}
          className="flex w-full items-center justify-between bg-gradient-to-r from-emerald-600 to-teal-500 px-3 py-2 text-white"
        >
          <span className="flex items-center gap-2 text-xs font-semibold">
            <BsShieldCheck />
            Proctoring {isConnected ? "Active" : status === "connecting" ? "Connecting…" : "Off"}
          </span>
          <span className="text-xs">{minimized ? "▲" : "▼"}</span>
        </button>

        {!minimized && (
          <div className="space-y-3 p-3">
            <div className="relative overflow-hidden rounded-xl bg-black">
              <video
                ref={videoRef}
                muted
                playsInline
                className="h-32 w-full object-cover"
              />
              <canvas ref={canvasRef} className="hidden" />
              {!isConnected && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/50 text-[11px] text-white">
                  {error ? "Camera unavailable" : "Waiting to connect…"}
                </div>
              )}
            </div>

            {behavior && (
              <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] text-gray-600">
                <ScoreRow label="Attention" value={behavior.attention} />
                <ScoreRow label="Confidence" value={behavior.confidence} />
                <ScoreRow label="Engagement" value={behavior.engagement} />
                <ScoreRow label="Calmness" value={behavior.calmness} />
              </div>
            )}

            <div className="flex items-center justify-between text-[11px]">
              <span className="text-gray-500">Suspicious activity</span>
              <span
                className={`font-semibold ${
                  suspicious > 50 ? "text-red-600" : suspicious > 20 ? "text-amber-600" : "text-emerald-600"
                }`}
              >
                {Math.round(suspicious)}%
              </span>
            </div>

            {error && (
              <p className="text-[10px] text-gray-400">
                Proctoring is offline — your interview continues normally.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ScoreRow({ label, value }) {
  return (
    <div className="flex items-center justify-between">
      <span>{label}</span>
      <span className="font-semibold text-emerald-600">{Math.round(value)}</span>
    </div>
  );
}

export default ProctoringPanel;
