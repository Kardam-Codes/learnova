/*
 * File: LoadingBlock.jsx
 * Owner: BOTH CAN ADD
 * Purpose: Standardize loading placeholders across learner and instructor pages.
 * What it is: A lightweight loading surface that avoids raw text-only loading states.
 */
export default function LoadingBlock({ title = "Loading", description = "Please wait while we prepare this view.", compact = false }) {
  return (
    <section className={`loading-block${compact ? " is-compact" : ""}`} aria-live="polite" aria-busy="true">
      <div className="loading-block-bar" />
      <div className="loading-block-copy">
        <strong>{title}</strong>
        <p>{description}</p>
      </div>
    </section>
  );
}
