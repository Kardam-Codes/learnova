/*
 * File: InstructorNavbar.jsx
 * Owner: YUG
 * Purpose: Provide one consistent navigation bar for all instructor and organiser pages.
 * What it is: A reusable instructor header with brand, primary navigation, and utility actions.
 */
import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function BrandLogoIcon() {
  return (
    <svg viewBox="0 0 64 64" className="brand-logo-icon" aria-hidden="true">
      <rect width="64" height="64" rx="10" fill="currentColor" opacity="0.12" />
      <path d="M12 12h12v28h16v12H12Z" fill="currentColor" />
      <path d="M28 12h24v12H40v16H28Z" fill="currentColor" opacity="0.9" />
      <path d="M40 24h12v28H24V40h16Z" fill="none" stroke="currentColor" strokeWidth="6" strokeLinejoin="round" />
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

export default function InstructorNavbar({ theme, toggleTheme }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const displayName = user?.name ?? "Instructor";
  const [isHidden, setIsHidden] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);
  const lastScrollY = useRef(0);

  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;
      const delta = currentScrollY - lastScrollY.current;

      setIsScrolled(currentScrollY > 10);

      if (currentScrollY <= 18) {
        setIsHidden(false);
      } else if (delta > 8) {
        setIsHidden(true);
      } else if (delta < -6) {
        setIsHidden(false);
      }

      lastScrollY.current = currentScrollY;
    };

    lastScrollY.current = window.scrollY;
    window.addEventListener("scroll", handleScroll, { passive: true });

    return () => {
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);

  const searchParams = new URLSearchParams(location.search);
  const courseFromQuery = searchParams.get("course");
  const courseFromPathMatch = location.pathname.match(/^\/instructor\/courses\/([^/]+)\/edit$/);
  const activeCourseSlug = courseFromPathMatch?.[1] ?? courseFromQuery ?? "new-course";
  const navItems = [
    { label: "Courses", to: "/instructor/courses" },
    { label: "Reporting", to: "/instructor/reports" },
    { label: "Setting", to: `/instructor/courses/${activeCourseSlug}/edit` },
  ];

  return (
    <header className={`page-navbar instructor-navbar${isHidden ? " is-hidden" : ""}${isScrolled ? " is-scrolled" : ""}`}>
      <Link className="brand-lockup brand-wordmark-link" to="/instructor/courses">
        <BrandLogoIcon />
        <h1 className="brand-wordmark">Learnova</h1>
      </Link>

      <nav className="instructor-nav-links" aria-label="Instructor navigation">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `instructor-nav-link${isActive ? " is-active" : ""}`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="navbar-actions instructor-navbar-actions">
        <button
          type="button"
          className="theme-toggle"
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
          title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
        >
          <ThemeIcon theme={theme} />
        </button>
        <div className="learner-badge instructor-user-badge" aria-label={`Signed in as ${displayName}`}>
          <strong>{displayName}</strong>
        </div>
        <div className="profile-avatar" aria-hidden="true">
          {displayName.slice(0, 1)}
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
      </div>
    </header>
  );
}
