/*
 * File: CourseDetailPage.jsx
 * Owner: KARDAM
 * Purpose: Render the learner-facing course overview screen for an enrolled course.
 * What it is: Page-level container that wires mock course data into the overview layout and title search.
 */
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Navbar from "../components/Navbar";
import CourseHeader from "../components/CourseHeader";
import CourseTabs from "../components/CourseTabs";
import ContentSearch from "../components/ContentSearch";
import ContentList from "../components/ContentList";
import StatusBanner from "../components/StatusBanner";
import LoadingBlock from "../components/LoadingBlock";
import { useAuth } from "../context/AuthContext";
import { fetchCourseDetailRequest } from "../utils/apiClient";
import { getCourseDetailMock } from "../data/courseDetailMock";

export default function CourseDetailPage({ theme, toggleTheme }) {
  const { courseId = "odoo-crm" } = useParams();
  const { token } = useAuth();
  const [query, setQuery] = useState("");
  const [course, setCourse] = useState(() => getCourseDetailMock(courseId));
  const [loadError, setLoadError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    const loadCourse = async () => {
      setIsLoading(true);
      try {
        const response = await fetchCourseDetailRequest(courseId, token);
        if (isMounted) {
          setCourse(response);
          setLoadError("");
        }
      } catch {
        if (isMounted) {
          setCourse(getCourseDetailMock(courseId));
          setLoadError("Live course details could not be loaded. Showing fallback content.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    if (token) {
      loadCourse();
    }

    return () => {
      isMounted = false;
    };
  }, [courseId, token]);

  // Search only narrows the visible list. Progress numbers remain course-wide.
  const normalizedQuery = query.trim().toLowerCase();
  const filteredItems = course.contentItems
    .filter((item) =>
      normalizedQuery ? item.title.toLowerCase().includes(normalizedQuery) : true,
    )
    .sort((left, right) => left.order - right.order);

  return (
    <main className="course-page-shell">
      <Navbar
        brandName={course.providerName}
        learnerName={course.learnerName}
        theme={theme}
        toggleTheme={toggleTheme}
      />

      <div className="course-page-card">
        <StatusBanner
          tone={loadError ? "error" : "info"}
          message={loadError}
          onClose={() => setLoadError("")}
        />
        {isLoading ? (
          <LoadingBlock
            title="Loading course details"
            description="Preparing the course overview, progress, and content list."
          />
        ) : (
          <>
        <CourseHeader course={course} />

        <div className="course-toolbar">
          <CourseTabs courseId={course.id} />
          <ContentSearch value={query} onChange={setQuery} />
        </div>

        <ContentList
          items={filteredItems}
          totalCount={course.progress.totalCount}
        />
          </>
        )}
      </div>
    </main>
  );
}
