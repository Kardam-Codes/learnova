/*
 * File: LessonPlayerPage.jsx
 * Owner: KARDAM
 * Purpose: Provide the destination route for course content clicks.
 * What it is: Placeholder player screen that proves lesson/quiz navigation and future player layout direction.
 */
import { Link, useParams } from "react-router-dom";
import { getCourseDetailMock } from "../data/courseDetailMock";

export default function LessonPlayerPage() {
  const { courseId, contentId } = useParams();
  // This page is intentionally lightweight for now and exists to complete navigation flow.
  const course = getCourseDetailMock(courseId);
  const contentItem = course.contentItems.find(
    (item) => item.id === contentId,
  );

  return (
    <main className="player-shell">
      <aside className="player-sidebar">
        <span className="eyebrow">Up next</span>
        <h2>{course.title}</h2>
        <p>{course.progress.completionPercentage}% completed</p>
        {/* Sidebar previews the same mixed content list that the learner came from. */}
        <div className="player-sidebar-list">
          {course.contentItems.map((item) => (
            <div
              key={item.id}
              className={`player-sidebar-item ${item.id === contentId ? "is-active" : ""}`}
            >
              {item.title}
            </div>
          ))}
        </div>
      </aside>

      <section className="player-content">
        <Link className="back-link" to={`/courses/${courseId}`}>
          Back to course overview
        </Link>
        <span className="sticker">Player route ready</span>
        <h1>{contentItem?.title ?? "Content not found"}</h1>
        <p>
          This placeholder keeps the course detail page navigation complete. The
          full-screen lesson player can now be built on top of this route.
        </p>
      </section>
    </main>
  );
}
