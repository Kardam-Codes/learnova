/*
 * File: CourseReviewsPage.jsx
 * Owner: KARDAM
 * Purpose: Reserve the separate route for course ratings and reviews.
 * What it is: Placeholder page that keeps navigation complete until the real reviews experience is built.
 */
import { Link, useParams } from "react-router-dom";
import Navbar from "../components/Navbar";
import CourseTabs from "../components/CourseTabs";
import { getCourseDetailMock } from "../data/courseDetailMock";

export default function CourseReviewsPage() {
  const { courseId } = useParams();
  const course = getCourseDetailMock(courseId);

  return (
    <main className="course-page-shell">
      <Navbar brandName={course.providerName} learnerName={course.learnerName} />

      <div className="course-page-card reviews-shell">
        <div className="reviews-header">
          <div>
            <span className="eyebrow">Course reviews</span>
            <h2>{course.title}</h2>
          </div>
          <Link className="back-link" to={`/courses/${courseId}`}>
            Back to overview
          </Link>
        </div>

        <CourseTabs courseId={course.id} />

        {/* Reviews remain a deliberate placeholder until the dedicated page is built. */}
        <section className="placeholder-panel">
          <span className="sticker">Next phase</span>
          <h3>Ratings and Reviews will be built on a dedicated page.</h3>
          <p>
            The navigation is already wired, so we can plug in the review summary
            and learner feedback flow later without changing the course overview.
          </p>
        </section>
      </div>
    </main>
  );
}
