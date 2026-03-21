/*
 * File: InviteAttendeeModal.jsx
 * Owner: BOTH CAN ADD
 * Purpose: Collect attendee details without relying on browser prompts.
 * What it is: A small modal form for adding course attendees from the instructor course page.
 */
import { useState } from "react";
import Modal from "./Modal";

export default function InviteAttendeeModal({
  accessRule,
  isSubmitting,
  onClose,
  onSubmit,
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    await onSubmit({
      name: name.trim(),
      email: email.trim(),
      enrollmentSource: "invited",
      paymentStatus: accessRule === "payment" ? "pending" : "not_required",
    });
  };

  return (
    <Modal title="Add Attendee" onClose={onClose}>
      <form className="dialog-stack" onSubmit={handleSubmit}>
        <p className="dialog-copy">Invite a learner and enrol them directly into this course.</p>

        <label className="auth-field dialog-field">
          <span>Name</span>
          <input
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Enter attendee name"
            required
          />
        </label>

        <label className="auth-field dialog-field">
          <span>Email</span>
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="learner@example.com"
            required
          />
        </label>

        <div className="dialog-actions">
          <button type="button" className="catalog-action-button instructor-ghost-button" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="catalog-action-button instructor-cta-button" disabled={isSubmitting}>
            {isSubmitting ? "Adding..." : "Add Attendee"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
