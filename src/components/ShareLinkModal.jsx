/*
 * File: ShareLinkModal.jsx
 * Owner: BOTH CAN ADD
 * Purpose: Let instructors copy or inspect a shareable learner course link.
 * What it is: A modal wrapper around the shared modal shell with explicit copy UX.
 */
import Modal from "./Modal";

export default function ShareLinkModal({ courseTitle, courseUrl, onClose, onCopy, isCopying }) {
  return (
    <Modal title="Share Course" onClose={onClose}>
      <div className="dialog-stack">
        <p className="dialog-copy">
          Share <strong>{courseTitle}</strong> with learners using the link below.
        </p>

        <label className="auth-field dialog-field">
          <span>Course Link</span>
          <input type="text" value={courseUrl} readOnly />
        </label>

        <div className="dialog-actions">
          <button type="button" className="catalog-action-button instructor-ghost-button" onClick={onClose}>
            Close
          </button>
          <button type="button" className="catalog-action-button instructor-cta-button" onClick={onCopy} disabled={isCopying}>
            {isCopying ? "Copying..." : "Copy Link"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
