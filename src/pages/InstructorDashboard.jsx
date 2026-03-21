/*
 * File: InstructorDashboard.jsx
 * Owner: YUG
 * Purpose: Render the instructor course management dashboard in both list and kanban views.
 * What it is: A route-level page that shows searchable live course records with actions for edit, share, and creation.
 */
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import InstructorNavbar from "../components/InstructorNavbar";
import { instructorCourses } from "../data/instructorMock";
import { useAuth } from "../context/AuthContext";
import { fetchAdminCoursesRequest } from "../utils/apiClient";

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

function mapApiCourseToDashboardCourse(course) {
  return {
    id: course.slug,
    title: course.title,
    tags: course.tags ?? [],
    views: 0,
    contents: course.contentCount ?? 0,
    duration: "-",
    isPublished: Boolean(course.isPublished),
  };
}

export default function InstructorDashboard() {
  const { token } = useAuth();
  const [query, setQuery] = useState("");
  const [viewMode, setViewMode] = useState("list");
  const [courses, setCourses] = useState(instructorCourses);
  const [loadError, setLoadError] = useState("");
  const normalizedQuery = query.trim().toLowerCase();

  useEffect(() => {
    let isMounted = true;

    const loadCourses = async () => {
      try {
        const response = await fetchAdminCoursesRequest(token);
        if (!isMounted) {
          return;
        }

        setCourses(response.courses.map(mapApiCourseToDashboardCourse));
        setLoadError("");
      } catch (error) {
        if (!isMounted) {
          return;
        }

        setCourses(instructorCourses);
        setLoadError(error.message);
      }
    };

    if (token) {
      loadCourses();
    }

    return () => {
      isMounted = false;
    };
  }, [token]);

  // Search checks both course titles and tags so instructors can quickly locate a record.
  const filteredCourses = useMemo(() => {
    return courses.filter((course) => {
      const searchTarget = [course.title, ...course.tags].join(" ").toLowerCase();
      return normalizedQuery ? searchTarget.includes(normalizedQuery) : true;
    });
  }, [courses, normalizedQuery]);

  const handleShareCourse = async (courseId) => {
    const shareUrl = `${window.location.origin}/courses/${courseId}`;

    try {
      await navigator.clipboard.writeText(shareUrl);
      window.alert("Course link copied to clipboard.");
    } catch {
      window.prompt("Copy this course link", shareUrl);
    }
  };

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

          {loadError ? (
            <p className="content-empty">
              Live course data could not be loaded. Showing fallback records.
            </p>
          ) : null}

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
                      <span key={tag} className="course-item-tag">
                        {tag}
                      </span>
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
                  <button
                    type="button"
                    className="catalog-action-button instructor-ghost-button"
                    onClick={() => handleShareCourse(course.id)}
                  >
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
