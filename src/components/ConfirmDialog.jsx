/*
 * File: ConfirmDialog.jsx
 * Owner: BOTH CAN ADD
 * Purpose: Replace destructive browser confirmation shortcuts with an in-app dialog.
 * What it is: A reusable confirmation modal for delete and other irreversible actions.
 */
import Modal from "./Modal";

export default function ConfirmDialog({
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  tone = "danger",
  isSubmitting = false,
  onConfirm,
  onClose,
}) {
  return (
    <Modal title={title} onClose={onClose}>
      <div className="dialog-stack">
        <p className="dialog-copy">{description}</p>
        <div className="dialog-actions">
          <button type="button" className="catalog-action-button instructor-ghost-button" onClick={onClose}>
            {cancelLabel}
          </button>
          <button
            type="button"
            className={`catalog-action-button ${tone === "danger" ? "danger-action-button" : "instructor-cta-button"}`}
            onClick={onConfirm}
            disabled={isSubmitting}
          >
            {isSubmitting ? "Working..." : confirmLabel}
          </button>
        </div>
      </div>
    </Modal>
  );
}
