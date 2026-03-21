import ProgressPanel from "./ProgressPanel";

export default function CourseHeader({ course }) {
  return (
    <section className="course-hero">
      {/* Left column holds course identity and short explanation. */}
      <div className="course-summary">
        <img
          className="course-thumbnail"
          src={course.thumbnail}
          alt={`${course.title} thumbnail`}
        />
        <div className="course-summary-copy">
          <span className="sticker">Course</span>
          <h2>{course.title}</h2>
          <p>{course.shortDescription}</p>
        </div>
      </div>

      {/* Center panel acts as the large editorial cover image. */}
      <div className="course-cover-panel">
        <img src={course.coverImage} alt={`${course.title} cover`} />
      </div>

      {/* Right column is reserved for learner progress and stat cards. */}
      <ProgressPanel progress={course.progress} />
    </section>
  );
}
