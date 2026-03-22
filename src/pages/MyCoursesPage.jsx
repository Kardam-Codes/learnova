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
import { useAuth } from "../context/AuthContext";
import { enrollCourseRequest, fetchCoursesRequest } from "../utils/apiClient";

const EMPTY_PROFILE = {
  learnerName: "Learner",
  totalPoints: 0,
  currentBadge: "Newbie",
  badgeTiers: [],
};

export default function MyCoursesPage({ theme, toggleTheme }) {
  const { token, user } = useAuth();
  const [query, setQuery] = useState("");
  const [catalogData, setCatalogData] = useState({
    profile: EMPTY_PROFILE,
    courses: [],
    enrolledCourses: [],
    availableCourses: [],
  });
  const [loadError, setLoadError] = useState("");
  const [actionMessage, setActionMessage] = useState("");
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
            learnerName: response.profile.learnerName || user?.name || EMPTY_PROFILE.learnerName,
          },
          courses: response.courses ?? response.enrolledCourses ?? [],
          enrolledCourses: response.enrolledCourses ?? response.courses ?? [],
          availableCourses: response.availableCourses ?? [],
        });
        setLoadError("");
      } catch {
        if (!isMounted) {
          return;
        }
        setCatalogData({
          profile: {
            ...EMPTY_PROFILE,
            learnerName: user?.name || EMPTY_PROFILE.learnerName,
          },
          courses: [],
          enrolledCourses: [],
          availableCourses: [],
        });
        setLoadError("Live catalog data could not be loaded right now.");
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

  const matchesQuery = (course) => {
    if (!normalizedQuery) {
      return true;
    }

    return course.title.toLowerCase().includes(normalizedQuery);
  };

  const filteredEnrolledCourses = catalogData.enrolledCourses.filter(matchesQuery);
  const filteredAvailableCourses = catalogData.availableCourses.filter(matchesQuery);

  const handleEnrollCourse = async (course) => {
    try {
      await enrollCourseRequest(course.id, token);
      const refreshed = await fetchCoursesRequest(token);
      setCatalogData({
        profile: {
          ...refreshed.profile,
          learnerName: refreshed.profile.learnerName || user?.name || EMPTY_PROFILE.learnerName,
        },
        courses: refreshed.courses ?? refreshed.enrolledCourses ?? [],
        enrolledCourses: refreshed.enrolledCourses ?? refreshed.courses ?? [],
        availableCourses: refreshed.availableCourses ?? [],
      });
      setActionMessage(`You are now enrolled in ${course.title}.`);
      setLoadError("");
    } catch (error) {
      setLoadError(error.message || "Course enrollment could not be completed.");
    }
  };

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
        <StatusBanner
          tone="success"
          message={actionMessage}
          onClose={() => setActionMessage("")}
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
            placeholder="Search course name"
          />
        </div>

        <div className="my-courses-layout">
          <div className="catalog-sections">
            {isLoading ? (
              <LoadingBlock
                title="Loading your courses"
                description="Fetching your enrolled and available courses."
              />
            ) : (
              <>
                <section className="catalog-section">
                  <div className="catalog-section-header">
                    <span className="eyebrow">Learning now</span>
                    <h2>Enrolled Courses</h2>
                  </div>
                  {filteredEnrolledCourses.length ? (
                    <CourseGrid courses={filteredEnrolledCourses} onEnrollCourse={handleEnrollCourse} />
                  ) : (
                    <EmptyState
                      title="No enrolled courses yet"
                      description="Enroll in a free course or complete a paid checkout to start building your learning path."
                    />
                  )}
                </section>

                <section className="catalog-section">
                  <div className="catalog-section-header">
                    <span className="eyebrow">Browse catalog</span>
                    <h2>All Courses</h2>
                  </div>
                  {filteredAvailableCourses.length ? (
                    <CourseGrid courses={filteredAvailableCourses} onEnrollCourse={handleEnrollCourse} />
                  ) : (
                    <EmptyState
                      title="No additional courses found"
                      description="Try a different search term or clear the search to browse the full published catalog."
                    />
                  )}
                </section>
              </>
            )}
          </div>
          <ProfilePanel profile={catalogData.profile} />
        </div>
      </div>
    </main>
  );
}
