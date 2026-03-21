/*
 * File: Modal.jsx
 * Owner: KARDAM
 * Purpose: Provide the forgot-password dialog shell.
 * What it is: A simple overlay modal for auth-side secondary actions.
 */
export default function Modal({ title, children, onClose }) {
  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label={title}>
      <div className="modal-card">
        <div className="modal-header">
          <h2>{title}</h2>
          <button type="button" className="modal-close-button" onClick={onClose}>
            <svg viewBox="0 0 24 24" className="inline-icon" aria-hidden="true">
              <path d="M7 7 17 17M17 7 7 17" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
            </svg>
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
