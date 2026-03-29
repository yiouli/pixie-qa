import { useEffect, useCallback } from "react";

export interface EvalDetailData {
  score: number;
  reasoning: string;
  input?: string;
  expectedOutput?: string;
  actualOutput?: string;
  metadata?: Record<string, unknown>;
}

interface EvalDetailModalProps {
  data: EvalDetailData | null;
  onClose: () => void;
}

export function EvalDetailModal({ data, onClose }: EvalDetailModalProps) {
  const handleKey = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (data) {
      document.body.classList.add("modal-open");
      document.addEventListener("keydown", handleKey);
    }
    return () => {
      document.body.classList.remove("modal-open");
      document.removeEventListener("keydown", handleKey);
    };
  }, [data, handleKey]);

  if (!data) return null;

  const passed = data.score >= 0.5;
  const hasMetadata = data.metadata && Object.keys(data.metadata).length > 0;

  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal-card" role="dialog" aria-modal="true">
        <button
          type="button"
          className="modal-close"
          aria-label="Close detail view"
          onClick={onClose}
        >
          ×
        </button>

        <h2 className="modal-title">Evaluation detail</h2>

        <div className="eval-detail-body">
          <div className="eval-detail-row">
            <span className="eval-detail-label">Score</span>
            <span className={`eval-detail-score ${passed ? "pass" : "fail"}`}>
              {data.score.toFixed(2)} {passed ? "✓" : "✗"}
            </span>
          </div>

          <div className="eval-detail-row">
            <span className="eval-detail-label">Reasoning</span>
            <span className="eval-detail-value">
              {data.reasoning || "(none)"}
            </span>
          </div>

          <div className="eval-detail-row">
            <span className="eval-detail-label">Input</span>
            <pre className="eval-detail-json">{data.input ?? "(none)"}</pre>
          </div>

          {data.expectedOutput != null && (
            <div className="eval-detail-row">
              <span className="eval-detail-label">Expected output</span>
              <pre className="eval-detail-json">{data.expectedOutput}</pre>
            </div>
          )}

          <div className="eval-detail-row">
            <span className="eval-detail-label">Actual output</span>
            <pre className="eval-detail-json">
              {data.actualOutput ?? "(none)"}
            </pre>
          </div>

          {hasMetadata && (
            <div className="eval-detail-row">
              <span className="eval-detail-label">Metadata</span>
              <pre className="eval-detail-json">
                {JSON.stringify(data.metadata, null, 2)}
              </pre>
            </div>
          )}
        </div>

        <div className="modal-actions">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
