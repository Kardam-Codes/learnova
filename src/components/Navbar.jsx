/*
 * File: Navbar.jsx
 * Owner: KARDAM
 * Purpose: Show the shared top navigation across learner-facing pages.
 * What it is: A reusable header with brand identity, learner account state, and theme switching.
 */
function ThemeIcon({ theme }) {
  if (theme === "light") {
    return (
      <svg className="theme-icon" viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="12" r="4.5" fill="currentColor" />
        <path
          d="M12 2.5V5.5M12 18.5V21.5M21.5 12H18.5M5.5 12H2.5M18.7 5.3L16.6 7.4M7.4 16.6L5.3 18.7M18.7 18.7L16.6 16.6M7.4 7.4L5.3 5.3"
          fill="none"
          stroke="currentColor"
          strokeLinecap="round"
          strokeWidth="2"
        />
      </svg>
    );
  }

  return (
    <svg className="theme-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M15.4 3.5C11.2 4 8 7.6 8 11.9c0 4.8 3.9 8.6 8.6 8.6 2.1 0 4.1-.7 5.7-2.1-1 .2-1.6.3-2.4.3-5 0-9.1-4.1-9.1-9.1 0-2.3.8-4.4 2.2-6.1 1-.1 1.5-.1 2.4 0z"
        fill="currentColor"
      />
    </svg>
  );
}

export default function Navbar({ brandName, learnerName, theme, toggleTheme }) {
  return (
    <header className="page-navbar">
      {/* Brand area keeps the product identity visible on learner pages. */}
      <div className="brand-lockup">
        <span className="brand-chip">Learner Space</span>
        <h1>{brandName}</h1>
      </div>

      <div className="navbar-actions">
        {/* Theme toggle sits in the upper-right controls and flips the global page palette. */}
        <button
          type="button"
          className="theme-toggle"
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
          title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
        >
          <ThemeIcon theme={theme} />
          <span>{theme === "light" ? "Light" : "Dark"}</span>
        </button>

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
      </div>
    </header>
  );
}
