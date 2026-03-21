/*
 * File: EmptyState.jsx
 * Owner: BOTH CAN ADD
 * Purpose: Give empty collections and filtered results a polished fallback surface.
 * What it is: A reusable empty-state block with optional title, description, and action area.
 */
export default function EmptyState({ title, description, action, compact = false }) {
  return (
    <section className={`empty-state${compact ? " is-compact" : ""}`}>
      <div className="empty-state-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" className="inline-icon">
          <rect x="4.5" y="5.5" width="15" height="13" rx="2.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
          <path d="M8 10h8M8 14h5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      </div>
      <div className="empty-state-copy">
        <strong>{title}</strong>
        {description ? <p>{description}</p> : null}
      </div>
      {action ? <div className="empty-state-action">{action}</div> : null}
    </section>
  );
}
