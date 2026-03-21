/*
 * File: CourseDetailPage.jsx
 * Owner: KARDAM
 * Purpose: Render the learner-facing course overview screen for an enrolled course.
 * What it is: Page-level container that wires mock course data into the overview layout and title search.
 */
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import Navbar from "../components/Navbar";
import CourseHeader from "../components/CourseHeader";
import CourseTabs from "../components/CourseTabs";
import ContentSearch from "../components/ContentSearch";
import ContentList from "../components/ContentList";
import StatusBanner from "../components/StatusBanner";
import LoadingBlock from "../components/LoadingBlock";
import { useAuth } from "../context/AuthContext";
import { enrollCourseRequest, fetchCourseDetailRequest } from "../utils/apiClient";

const EMPTY_COURSE = {
  id: "",
  title: "",
  shortDescription: "",
  thumbnail: "",
  providerName: "Learnova",
  learnerName: "",
  isEnrolled: false,
  paymentStatus: "pending",
  accessRule: "open",
  canEnrollFree: false,
  requiresPayment: false,
  progress: {
    completionPercentage: 0,
    totalCount: 0,
    completedCount: 0,
    incompleteCount: 0,
  },
  contentItems: [],
  reviews: {
    averageRating: 0,
    totalReviews: 0,
    items: [],
    learnerDraft: "",
  },
};

export default function CourseDetailPage({ theme, toggleTheme }) {
  const { courseId = "odoo-crm" } = useParams();
  const navigate = useNavigate();
  const { token } = useAuth();
  const [query, setQuery] = useState("");
  const [course, setCourse] = useState(EMPTY_COURSE);
  const [loadError, setLoadError] = useState("");
  const [actionMessage, setActionMessage] = useState("");
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
      } catch (error) {
        if (isMounted) {
          setCourse(EMPTY_COURSE);
          setLoadError(error.message || "Live course details could not be loaded.");
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

  const handleFreeEnrollment = async () => {
    try {
      const response = await enrollCourseRequest(courseId, token);
      setCourse(response);
      setActionMessage(`You are now enrolled in ${response.title}.`);
      setLoadError("");
    } catch (error) {
      setLoadError(error.message || "Course enrollment could not be completed.");
    }
  };

  // Search only narrows the visible list. Progress numbers remain course-wide.
  const normalizedQuery = query.trim().toLowerCase();
  const filteredItems = course.contentItems
    .filter((item) =>
      normalizedQuery ? item.title.toLowerCase().includes(normalizedQuery) : true,
    )
    .sort((left, right) => left.order - right.order);

  const heroAction = course.canEnrollFree ? (
    <button
      type="button"
      className="catalog-action-button is-enroll"
      onClick={handleFreeEnrollment}
    >
      Enroll Free
    </button>
  ) : course.requiresPayment ? (
    <button
      type="button"
      className="catalog-action-button is-buy"
      onClick={() => navigate(`/courses/${course.id}/payment`)}
    >
      Buy Course
    </button>
  ) : null;

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
        <StatusBanner
          tone="success"
          message={actionMessage}
          onClose={() => setActionMessage("")}
        />
        {isLoading ? (
          <LoadingBlock
            title="Loading course details"
            description="Preparing the course overview, progress, and content list."
          />
        ) : (
          <>
        <CourseHeader course={course} action={heroAction} />

        <div className="course-toolbar">
          <CourseTabs courseId={course.id} />
          <ContentSearch value={query} onChange={setQuery} />
        </div>

        {!course.isEnrolled ? (
          <section className="course-lock-panel">
            <span className="eyebrow">Course access</span>
            <h3>This course is locked until you enroll.</h3>
            <p>
              {course.requiresPayment
                ? "Complete the course payment to unlock its lessons, reviews, and quiz."
                : "Enroll first to unlock the course content, even though this course is free."}
            </p>
            {course.requiresPayment ? (
              <Link className="catalog-action-button is-buy" to={`/courses/${course.id}/payment`}>
                Continue to Payment
              </Link>
            ) : course.canEnrollFree ? (
              <button type="button" className="catalog-action-button is-enroll" onClick={handleFreeEnrollment}>
                Enroll Free
              </button>
            ) : null}
          </section>
        ) : null}

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
