/*
 * File: Navbar.jsx
 * Owner: KARDAM
 * Purpose: Show the shared top navigation across learner-facing pages.
 * What it is: A reusable header with brand identity and learner account state.
 */
export default function Navbar({ brandName, learnerName }) {
  return (
    <header className="page-navbar">
      {/* Brand area keeps the product identity visible on learner pages. */}
      <div className="brand-lockup">
        <span className="brand-chip">Learner Space</span>
        <h1>{brandName}</h1>
      </div>

      {/* This page only supports the logged-in learner state for now. */}
      <div className="learner-badge" aria-label={`Signed in as ${learnerName}`}>
        <div className="learner-copy">
          <span className="eyebrow">Logged in</span>
          <strong>{learnerName}</strong>
        </div>
        <div className="profile-avatar" aria-hidden="true">
          {learnerName.slice(0, 1)}
        </div>
      </div>
    </header>
  );
}
