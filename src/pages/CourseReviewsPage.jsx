/*
 * File: CourseReviewsPage.jsx
 * Owner: KARDAM
 * Purpose: Render the ratings and reviews view for an enrolled course.
 * What it is: The review tab page with rating summary, learner review composer, and existing review feed.
 */
import Navbar from "../components/Navbar";
import CourseHeader from "../components/CourseHeader";
import CourseTabs from "../components/CourseTabs";
import StatusBanner from "../components/StatusBanner";
import EmptyState from "../components/EmptyState";
import LoadingBlock from "../components/LoadingBlock";
import { useParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  fetchCourseDetailRequest,
  fetchCourseReviewsRequest,
  submitCourseReviewRequest,
} from "../utils/apiClient";
import { useEffect, useState } from "react";

const EMPTY_COURSE = {
  id: "",
  title: "",
  shortDescription: "",
  thumbnail: "",
  providerName: "Learnova",
  learnerName: "",
  isEnrolled: false,
  progress: {
    completionPercentage: 0,
    totalCount: 0,
    completedCount: 0,
    incompleteCount: 0,
  },
  reviews: {
    averageRating: 0,
    totalReviews: 0,
    items: [],
    learnerDraft: "",
    isEnrolled: false,
  },
};

function StarIcon({ filled }) {
  return (
    <svg className={`review-star ${filled ? "is-filled" : ""}`} viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M12 2.8 14.9 8.7 21.4 9.6 16.7 14.2 17.8 20.8 12 17.7 6.2 20.8 7.3 14.2 2.6 9.6 9.1 8.7Z"
        fill="currentColor"
      />
    </svg>
  );
}

function ReviewStars({ rating }) {
  return (
    <div className="review-stars" aria-label={`${rating} out of 5`}>
      {Array.from({ length: 5 }, (_, index) => (
        <StarIcon key={index} filled={index < Math.round(rating)} />
      ))}
    </div>
  );
}

export default function CourseReviewsPage({ theme, toggleTheme }) {
  const { courseId } = useParams();
  const { token } = useAuth();
  const [course, setCourse] = useState(EMPTY_COURSE);
  const [reviewDraft, setReviewDraft] = useState(course.reviews.learnerDraft);
  const [reviewRating, setReviewRating] = useState(5);
  const [reviewError, setReviewError] = useState("");
  const [reviewSuccess, setReviewSuccess] = useState("");
  const [loadError, setLoadError] = useState("");
  const [isSavingReview, setIsSavingReview] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    const loadCourseReviews = async () => {
      setIsLoading(true);
      try {
        const [courseResponse, reviewsResponse] = await Promise.all([
          fetchCourseDetailRequest(courseId, token),
          fetchCourseReviewsRequest(courseId, token),
        ]);

        if (!isMounted) {
          return;
        }

        setCourse({
          ...courseResponse,
          reviews: reviewsResponse,
        });
        setReviewDraft(reviewsResponse.learnerDraft ?? "");
        setLoadError("");
      } catch (error) {
        if (isMounted) {
          setCourse(EMPTY_COURSE);
          setLoadError(error.message || "Live reviews could not be loaded.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    if (token) {
      loadCourseReviews();
    }

    return () => {
      isMounted = false;
    };
  }, [courseId, token]);

  const handleReviewSubmit = async () => {
    if (!course.isEnrolled) {
      setReviewError("Enroll in this course before posting a review.");
      return;
    }

    setIsSavingReview(true);
    setReviewError("");
    setReviewSuccess("");

    try {
      const reviewsResponse = await submitCourseReviewRequest(courseId, token, {
        rating: reviewRating,
        comment: reviewDraft,
      });

      setCourse((current) => ({
        ...current,
        reviews: reviewsResponse,
      }));
      setReviewDraft("");
      setReviewRating(5);
      setReviewSuccess("Your review was saved successfully.");
    } catch (error) {
      setReviewError(error.message);
    } finally {
      setIsSavingReview(false);
    }
  };

  return (
    <main className="course-page-shell">
      <Navbar
        brandName={course.providerName}
        learnerName={course.learnerName}
        theme={theme}
        toggleTheme={toggleTheme}
      />

      <div className="course-page-card reviews-page-shell">
        <StatusBanner
          tone={loadError ? "error" : "info"}
          message={loadError}
          onClose={() => setLoadError("")}
        />
        <StatusBanner
          tone="success"
          message={reviewSuccess}
          onClose={() => setReviewSuccess("")}
        />
        <StatusBanner
          tone="error"
          message={reviewError}
          onClose={() => setReviewError("")}
        />
        {isLoading ? (
          <LoadingBlock
            title="Loading ratings and reviews"
            description="Pulling learner feedback and course sentiment."
          />
        ) : (
          <>
          <CourseHeader course={course} />

          <div className="course-toolbar">
            <CourseTabs courseId={course.id} />
          </div>

          <section className="reviews-content">
          <div className="reviews-summary-card">
          <div className="reviews-score-block">
              <strong>{course.reviews.averageRating.toFixed(1)}</strong>
              <ReviewStars rating={course.reviews.averageRating} />
            </div>
            <button
              type="button"
              className="catalog-action-button is-buy reviews-add-button"
              onClick={handleReviewSubmit}
              disabled={isSavingReview || !reviewDraft.trim() || !course.isEnrolled}
            >
              {isSavingReview ? "Saving..." : "Add Review"}
            </button>
          </div>

          {!course.isEnrolled ? (
            <EmptyState
              compact
              title="Reviews unlock after enrollment"
              description="Enroll in the course first, then return here to rate and review the learning experience."
            />
          ) : null}

          <section className="review-entry-card">
            <div className="review-entry-header">
              <div className="review-avatar" aria-hidden="true">
                <svg viewBox="0 0 24 24" className="review-avatar-icon">
                  <circle cx="12" cy="8" r="4" fill="currentColor" />
                  <path d="M4 21c1.6-4.2 4.6-6.3 8-6.3S18.4 16.8 20 21" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
                </svg>
              </div>
              <strong>{course.learnerName}</strong>
            </div>
            <label className="review-rating-field">
              <span>Rating</span>
              <select
                className="review-rating-select"
                value={reviewRating}
                onChange={(event) => setReviewRating(Number(event.target.value))}
              >
                {[5, 4, 3, 2, 1].map((ratingOption) => (
                  <option key={ratingOption} value={ratingOption}>
                    {ratingOption} Stars
                  </option>
                ))}
              </select>
            </label>
            <textarea
              className="review-input"
              value={reviewDraft}
              onChange={(event) => setReviewDraft(event.target.value)}
              aria-label="Write your review"
              disabled={!course.isEnrolled}
              placeholder="Share what worked well, what could improve, and how this course helped you."
            />
          </section>

          <div className="review-list">
            {course.reviews.items.length ? course.reviews.items.map((review) => (
              <article className="review-card" key={review.id}>
                <div className="review-entry-header">
                  <div className="review-avatar" aria-hidden="true">
                    <svg viewBox="0 0 24 24" className="review-avatar-icon">
                      <circle cx="12" cy="8" r="4" fill="currentColor" />
                      <path d="M4 21c1.6-4.2 4.6-6.3 8-6.3S18.4 16.8 20 21" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
                    </svg>
                  </div>
                  <div className="review-meta">
                    <strong>{review.authorName}</strong>
                    <ReviewStars rating={review.rating} />
                  </div>
                </div>
                <p>{review.comment}</p>
              </article>
            )) : (
              <EmptyState
                compact
                title="No reviews yet"
                description="Be the first learner to share feedback for this course."
              />
            )}
          </div>
          </section>
          </>
        )}
      </div>
    </main>
  );
}
