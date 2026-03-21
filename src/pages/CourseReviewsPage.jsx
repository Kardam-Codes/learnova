/*
 * File: CourseReviewsPage.jsx
 * Owner: KARDAM
 * Purpose: Render the ratings and reviews view for an enrolled course.
 * What it is: The review tab page with rating summary, learner review composer, and existing review feed.
 */
import Navbar from "../components/Navbar";
import CourseHeader from "../components/CourseHeader";
import CourseTabs from "../components/CourseTabs";
import { getCourseDetailMock } from "../data/courseDetailMock";
import { useParams } from "react-router-dom";

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
  const course = getCourseDetailMock(courseId);

  return (
    <main className="course-page-shell">
      <Navbar
        brandName={course.providerName}
        learnerName={course.learnerName}
        theme={theme}
        toggleTheme={toggleTheme}
      />

      <div className="course-page-card reviews-page-shell">
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
            <button type="button" className="catalog-action-button is-buy reviews-add-button">
              Add Review
            </button>
          </div>

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
            <textarea
              className="review-input"
              defaultValue={course.reviews.learnerDraft}
              aria-label="Write your review"
            />
          </section>

          <div className="review-list">
            {course.reviews.items.map((review) => (
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
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
