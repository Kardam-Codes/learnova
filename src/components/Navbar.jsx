/*
 * File: Navbar.jsx
 * Owner: KARDAM
 * Purpose: Show the shared top navigation across learner-facing pages.
 * What it is: A reusable header with brand identity, learner account state, and theme switching.
 */
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function BrandLogoIcon() {
  return (
    <svg viewBox="0 0 32 32" className="brand-logo-icon" aria-hidden="true">
      <path d="M6 24V8h4v12h14v4Z" fill="currentColor" />
      <path d="M12 8h14v4H16v14h-4Z" fill="currentColor" opacity="0.72" />
      <path d="M20 14h6v12H14v-6h6Z" fill="none" stroke="currentColor" strokeWidth="2.6" />
    </svg>
  );
}

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
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuth();
  const resolvedLearnerName = user?.name ?? learnerName;

  return (
    <header className="page-navbar">
      {/* Brand area keeps the product identity visible on learner pages. */}
      <Link className="brand-lockup brand-wordmark-link" to={isAuthenticated ? "/my-courses" : "/auth/login"}>
        <BrandLogoIcon />
        <h1 className="brand-wordmark">Learnova</h1>
      </Link>

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
        </button>

        {isAuthenticated ? (
          <>
            <div className="learner-badge" aria-label={`Signed in as ${resolvedLearnerName}`}>
              <strong>{resolvedLearnerName}</strong>
            </div>
            <div className="profile-avatar" aria-hidden="true">
              {resolvedLearnerName.slice(0, 1)}
            </div>
            <button
              type="button"
              className="navbar-text-button"
              onClick={() => {
                logout();
                navigate("/auth/login");
              }}
            >
              Sign Out
            </button>
          </>
        ) : (
          <Link className="navbar-signin-link" to="/auth/login">
            <strong>Sign In</strong>
            <div className="profile-avatar" aria-hidden="true">
              <svg viewBox="0 0 24 24" className="inline-icon">
                <circle cx="12" cy="8" r="4" fill="currentColor" />
                <path d="M4 21c1.6-4.2 4.6-6.3 8-6.3S18.4 16.8 20 21" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
              </svg>
            </div>
          </Link>
        )}
      </div>
    </header>
  );
}
