import ProgressPanel from "./ProgressPanel";

export default function CourseHeader({ course, action }) {
  return (
    <section className="course-hero">
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
          {action ? <div className="course-summary-action">{action}</div> : null}
        </div>
      </div>
      <ProgressPanel progress={course.progress} />
    </section>
  );
}
