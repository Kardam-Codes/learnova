import { NavLink } from "react-router-dom";

export default function CourseTabs({ courseId }) {
  return (
    // Tabs are route-driven so Overview and Reviews can grow independently later.
    <nav className="course-tabs" aria-label="Course sections">
      <NavLink
        end
        to={`/courses/${courseId}`}
        className={({ isActive }) =>
          `course-tab ${isActive ? "is-active" : ""}`.trim()
        }
      >
        Course Overview
      </NavLink>
      <NavLink
        to={`/courses/${courseId}/reviews`}
        className={({ isActive }) =>
          `course-tab ${isActive ? "is-active" : ""}`.trim()
        }
      >
        Ratings and Reviews
      </NavLink>
    </nav>
  );
}
