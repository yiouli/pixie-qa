import { useState, useEffect, useCallback, useRef } from "react";

interface FeedbackModalProps {
  open: boolean;
  onClose: () => void;
  feedbackUrl: string;
  commandArgs: string;
  timestamp: string;
}

export function FeedbackModal({
  open,
  onClose,
  feedbackUrl,
  commandArgs,
  timestamp,
}: FeedbackModalProps) {
  const [submitState, setSubmitState] = useState<
    "idle" | "sending" | "success" | "error"
  >("idle");
  const formRef = useRef<HTMLFormElement>(null);

  const handleKey = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (open) {
      document.body.classList.add("modal-open");
      document.addEventListener("keydown", handleKey);
      setSubmitState("idle");
    }
    return () => {
      document.body.classList.remove("modal-open");
      document.removeEventListener("keydown", handleKey);
    };
  }, [open, handleKey]);

  if (!open) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formRef.current) return;

    setSubmitState("sending");
    const data = new FormData(formRef.current);
    fetch(feedbackUrl, { method: "POST", body: data })
      .then(() => {
        setSubmitState("success");
        setTimeout(() => {
          onClose();
          formRef.current?.reset();
        }, 1200);
      })
      .catch(() => {
        setSubmitState("error");
        setTimeout(() => setSubmitState("idle"), 2000);
      });
  };

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
          aria-label="Close feedback form"
          onClick={onClose}
        >
          ×
        </button>

        <h2 className="modal-title">Send feedback to Pixie</h2>
        <p className="modal-description">
          Tell us what worked, what felt confusing, or attach text artifacts
          that help us improve the scorecard experience.
        </p>

        <form ref={formRef} className="feedback-form" onSubmit={handleSubmit}>
          <input type="hidden" name="source" value="pixie-scorecard" />
          <input type="hidden" name="command_args" value={commandArgs} />
          <input type="hidden" name="generated_at" value={timestamp} />

          <label className="field-label" htmlFor="feedback-text">
            Feedback
          </label>
          <textarea
            id="feedback-text"
            name="feedback"
            rows={6}
            required
            placeholder="Share your feedback..."
          />

          <label className="field-label" htmlFor="feedback-email">
            Email (optional)
          </label>
          <input
            id="feedback-email"
            name="email"
            type="email"
            placeholder="you@example.com"
          />

          <label className="field-label" htmlFor="feedback-attachments">
            Text attachments (optional)
          </label>
          <input
            id="feedback-attachments"
            name="attachments"
            type="file"
            multiple
            accept=".txt,.md,.log,.json,text/plain"
          />

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <SubmitButton state={submitState} />
          </div>
        </form>
      </div>
    </div>
  );
}

function SubmitButton({
  state,
}: {
  state: "idle" | "sending" | "success" | "error";
}) {
  const classMap = {
    idle: "btn-primary",
    sending: "btn-primary",
    success: "btn-primary submit-success",
    error: "btn-primary submit-error",
  };

  const label = {
    idle: "Submit feedback",
    sending: "Sending…",
    success: "✓ Sent!",
    error: "✗ Failed — try again",
  };

  return (
    <button
      type="submit"
      className={classMap[state]}
      disabled={state !== "idle"}
    >
      {label[state]}
    </button>
  );
}
