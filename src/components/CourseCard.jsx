/*
 * File: CourseCard.jsx
 * Owner: KARDAM
 * Purpose: Display one course card with tags, access state, and pricing details.
 * What it is: The main reusable card component for the My Courses page grid.
 */
import { useNavigate } from "react-router-dom";
import { COURSE_ACCESS_STATE } from "../../shared/types/common_types";
import { getCourseDetailMock } from "../data/courseDetailMock";
import { buildLearningRoute } from "../utils/learningRoutes";
import ActionButton from "./ActionButton";
import TagBadge from "./TagBadge";

function getCourseAction(course) {
  const detail = getCourseDetailMock(course.id);
  const firstContent = detail.contentItems.find((item) => item.id === course.firstContentId);
  const lastContent = detail.contentItems.find((item) => item.id === course.lastContentId);

  if (!course.isLoggedIn) {
    return { label: "Join Course", to: "/my-courses", type: COURSE_ACCESS_STATE.JOIN };
  }

  if (course.isPaid && !course.isPurchased) {
    return {
      label: "Buy Course",
      to: `/courses/${course.id}/payment`,
      type: COURSE_ACCESS_STATE.BUY,
    };
  }

  if (course.isInProgress) {
    return {
      label: "Continue",
      to: buildLearningRoute(course.id, lastContent ?? detail.contentItems[0]),
      type: COURSE_ACCESS_STATE.CONTINUE,
    };
  }

  return {
    label: "Start Course",
    to: buildLearningRoute(course.id, firstContent ?? detail.contentItems[0]),
    type: COURSE_ACCESS_STATE.START,
  };
}

export default function CourseCard({ course }) {
  const navigate = useNavigate();
  const action = getCourseAction(course);
  const showPaidBadge = course.isPaid && course.isPurchased;
  const openCourseDetail = () => navigate(course.detailPath);
  const handleCardKeyDown = (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openCourseDetail();
    }
  };
  const stopCardNavigation = (event) => event.stopPropagation();

  return (
    <article
      className="course-card"
      role="link"
      tabIndex={0}
      aria-label={`Open ${course.title}`}
      onClick={openCourseDetail}
      onKeyDown={handleCardKeyDown}
    >
      <div className="course-card-cover">
        <img src={course.coverImage} alt={`${course.title} cover`} />
      </div>

      <div className="course-card-body">
        <div className="course-card-copy">
          <div className="course-card-topline">
            <span className="sticker">Course</span>
            {showPaidBadge ? <span className="catalog-paid-badge">Paid</span> : null}
          </div>

          <div className="course-card-title-link">
            <h3>{course.title}</h3>
          </div>

          <p>{course.shortDescription}</p>

          <div className="catalog-tags">
            {course.tags.map((tag) => (
              <TagBadge key={tag} tag={tag} />
            ))}
          </div>
        </div>

        <div className="course-card-footer">
          <ActionButton action={action} onClick={stopCardNavigation} />
          <div className="course-card-price">
            {course.isPaid ? `INR ${course.price}` : "Free"}
          </div>
        </div>
      </div>
    </article>
  );
}
