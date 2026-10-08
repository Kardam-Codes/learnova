/*
 * File: StatusBanner.jsx
 * Owner: BOTH CAN ADD
 * Purpose: Show lightweight page-level success, error, and info feedback.
 * What it is: A reusable inline banner used instead of browser alerts and plain placeholder text blocks.
 */
export default function StatusBanner({ tone = "info", message, onClose }) {
  if (!message) {
    return null;
  }

  return (
    <div className={`status-banner status-banner-${tone}`} role="status" aria-live="polite">
      <div className="status-banner-copy">
        <strong>{tone === "error" ? "Something went wrong" : tone === "success" ? "Success" : "Notice"}</strong>
        <span>{message}</span>
      </div>
      {onClose ? (
        <button type="button" className="status-banner-close" onClick={onClose} aria-label="Dismiss message">
          <svg viewBox="0 0 24 24" className="inline-icon" aria-hidden="true">
            <path d="M7 7 17 17M17 7 7 17" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
          </svg>
        </button>
      ) : null}
    </div>
  );
}
