/*
 * File: InstructorDashboard.jsx
 * Owner: YUG
 * Purpose: Render the instructor course management dashboard in both list and kanban views.
 * What it is: A route-level page that shows searchable course records with actions for edit, share, and creation.
 */
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import InstructorNavbar from "../components/InstructorNavbar";
import { instructorCourses } from "../data/instructorMock";

function ViewToggleIcon({ active, mode }) {
  return (
    <span className={`view-toggle-icon${active ? " is-active" : ""}`} aria-hidden="true">
      {mode === "kanban" ? (
        <svg viewBox="0 0 24 24">
          <rect x="3" y="3" width="7" height="18" rx="1" />
          <rect x="14" y="3" width="7" height="8" rx="1" />
          <rect x="14" y="13" width="7" height="8" rx="1" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24">
          <rect x="4" y="4" width="16" height="4" rx="1" />
          <rect x="4" y="10" width="16" height="4" rx="1" />
          <rect x="4" y="16" width="16" height="4" rx="1" />
        </svg>
      )}
    </span>
  );
}

export default function InstructorDashboard() {
  const [query, setQuery] = useState("");
  const [viewMode, setViewMode] = useState("list");
  const normalizedQuery = query.trim().toLowerCase();

  // Search checks both course titles and tags so instructors can quickly locate a record.
  const filteredCourses = useMemo(() => {
    return instructorCourses.filter((course) => {
      const searchTarget = [course.title, ...course.tags].join(" ").toLowerCase();
      return normalizedQuery ? searchTarget.includes(normalizedQuery) : true;
    });
  }, [normalizedQuery]);

  return (
    <main className="course-page-shell instructor-page-shell">
      <InstructorNavbar />

      <div className="course-page-card instructor-shell">
        <section className="instructor-board">
          <div className="instructor-board-toolbar">
            <input
              type="search"
              className="instructor-search-input"
              placeholder="Search course from search bar"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />

            <div className="view-toggle-group" aria-label="Choose dashboard view">
              {["kanban", "list"].map((mode) => (
                <button
                  key={mode}
                  type="button"
                  className={`view-toggle-button${viewMode === mode ? " is-active" : ""}`}
                  onClick={() => setViewMode(mode)}
                >
                  <ViewToggleIcon active={viewMode === mode} mode={mode} />
                  <span>{mode === "kanban" ? "Kanban view" : "List view"}</span>
                </button>
              ))}
            </div>
          </div>

          <div
            className={`instructor-course-collection${
              viewMode === "kanban" ? " is-kanban" : ""
            }`}
          >
            {filteredCourses.map((course) => (
              <article key={course.id} className="instructor-course-item">
                <div className="course-item-main">
                  <Link
                    to={`/instructor/courses/${course.id}/edit`}
                    className="course-item-title-link"
                  >
                    <h2>{course.title}</h2>
                  </Link>

                  <div className="course-item-tags" aria-label="Course tags">
                    {course.tags.map((tag) => (
                      <button key={tag} type="button" className="course-item-tag">
                        {tag}
                        <span aria-hidden="true">×</span>
                      </button>
                    ))}
                  </div>
                </div>

                <dl className="course-item-metrics">
                  <div>
                    <dt>Views</dt>
                    <dd>{course.views}</dd>
                  </div>
                  <div>
                    <dt>Contents</dt>
                    <dd>{course.contents}</dd>
                  </div>
                  <div>
                    <dt>Duration</dt>
                    <dd>{course.duration}</dd>
                  </div>
                </dl>

                <div className="course-item-actions">
                  <button type="button" className="catalog-action-button instructor-ghost-button">
                    Share
                  </button>
                  <Link
                    to={`/instructor/courses/${course.id}/edit`}
                    className="catalog-action-button instructor-ghost-button"
                  >
                    Edit
                  </Link>
                </div>

                {course.isPublished ? (
                  <span className="instructor-publish-ribbon">Published</span>
                ) : (
                  <span className="instructor-draft-badge">Draft</span>
                )}
              </article>
            ))}
          </div>

          <Link
            to="/instructor/courses/new-course/edit"
            className="instructor-floating-add"
            aria-label="Create a new course"
          >
            <svg viewBox="0 0 24 24">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
          </Link>
        </section>
      </div>
    </main>
  );
}
