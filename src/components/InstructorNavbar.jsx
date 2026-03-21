/*
 * File: InstructorNavbar.jsx
 * Owner: YUG
 * Purpose: Provide one consistent navigation bar for all instructor and organiser pages.
 * What it is: A reusable instructor header with brand, primary navigation, and utility actions.
 */
import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const navItems = [
  { label: "Courses", to: "/instructor/courses" },
  { label: "Reporting", to: "/instructor/reports" },
  { label: "Setting", to: "/instructor/courses/odoo-crm/edit" },
];

export default function InstructorNavbar() {
  const { user } = useAuth();
  const displayName = user?.name ?? "Instructor";

  return (
    <header className="page-navbar instructor-navbar">
      <div className="brand-lockup brand-wordmark-link">
        <h1 className="brand-wordmark">Learnova</h1>
      </div>

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

      <div className="learner-badge instructor-user-badge" aria-label={`Signed in as ${displayName}`}>
        <div className="learner-copy">
          <span className="eyebrow">Signed in</span>
          <strong>{displayName}</strong>
        </div>
        <div className="profile-avatar" aria-hidden="true">
          {displayName.slice(0, 1)}
        </div>
      </div>
    </header>
  );
}
