/*
 * File: MyCoursesPage.jsx
 * Owner: KARDAM
 * Purpose: Render the learner dashboard with searchable course cards and profile insights.
 * What it is: The new landing page for the learner's course catalog and gamified profile panel.
 */
import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import SearchBar from "../components/SearchBar";
import CourseGrid from "../components/CourseGrid";
import ProfilePanel from "../components/ProfilePanel";
import StatusBanner from "../components/StatusBanner";
import EmptyState from "../components/EmptyState";
import LoadingBlock from "../components/LoadingBlock";
import { learnerProfileMock, myCoursesMock } from "../data/myCoursesMock";
import { useAuth } from "../context/AuthContext";
import { fetchCoursesRequest } from "../utils/apiClient";

export default function MyCoursesPage({ theme, toggleTheme }) {
  const { token, user } = useAuth();
  const [query, setQuery] = useState("");
  const [catalogData, setCatalogData] = useState({
    profile: learnerProfileMock,
    courses: myCoursesMock,
  });
  const [loadError, setLoadError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const normalizedQuery = query.trim().toLowerCase();

  useEffect(() => {
    let isMounted = true;

    const loadCourses = async () => {
      setIsLoading(true);
      try {
        const response = await fetchCoursesRequest(token);
        if (!isMounted) {
          return;
        }

        setCatalogData({
          profile: {
            ...response.profile,
            learnerName: response.profile.learnerName || user?.name || learnerProfileMock.learnerName,
          },
          courses: response.courses,
        });
        setLoadError("");
      } catch {
        if (!isMounted) {
          return;
        }

        setCatalogData((current) => current);
        setLoadError("Live catalog data could not be loaded. Showing fallback course data.");
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    if (token) {
      loadCourses();
    }

    return () => {
      isMounted = false;
    };
  }, [token, user?.name]);

  const filteredCourses = catalogData.courses.filter((course) => {
    if (!normalizedQuery) {
      return true;
    }

    const searchTarget = [
      course.title,
      course.shortDescription,
      ...course.tags,
    ]
      .join(" ")
      .toLowerCase();

    return searchTarget.includes(normalizedQuery);
  });

  return (
    <main className="course-page-shell">
      <Navbar
        brandName="Learnova"
        learnerName={catalogData.profile.learnerName}
        theme={theme}
        toggleTheme={toggleTheme}
      />

      <div className="course-page-card my-courses-shell">
        <StatusBanner
          tone={loadError ? "error" : "info"}
          message={loadError}
          onClose={() => setLoadError("")}
        />
        <div className="my-courses-header">
          <div className="my-courses-heading">
            <span className="eyebrow">Learner Dashboard</span>
            <Link className="my-courses-title-link" to="/my-courses">
              <h1>My Courses</h1>
            </Link>
          </div>

          <SearchBar
            value={query}
            onChange={setQuery}
            placeholder="Search all courses"
          />
        </div>

        <div className="my-courses-layout">
          {isLoading ? (
            <LoadingBlock
              title="Loading your courses"
              description="Fetching your enrolled and available courses."
            />
          ) : filteredCourses.length ? (
            <CourseGrid courses={filteredCourses} />
          ) : (
            <EmptyState
              title="No courses found"
              description="Try a different search term or clear the filter to browse your full catalog."
            />
          )}
          <ProfilePanel profile={catalogData.profile} />
        </div>
      </div>
    </main>
  );
}
