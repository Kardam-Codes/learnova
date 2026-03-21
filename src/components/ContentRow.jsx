/*
 * File: ContentRow.jsx
 * Owner: KARDAM
 * Purpose: Render one clickable lesson/quiz row inside the mixed course content list.
 * What it is: A reusable presentational component that shows content type, title, meta, and progress status.
 */
import { Link, useParams } from "react-router-dom";
import StatusIndicator from "./StatusIndicator";
import { COURSE_CONTENT_STATUS } from "../../shared/types/common_types";
import { buildLearningRoute } from "../utils/learningRoutes";

const typeLabel = {
  document: "Document",
  video: "Video",
  quiz: "Quiz",
};

export default function ContentRow({ item }) {
  const { courseId } = useParams();
  const rowClassName =
    item.status === COURSE_CONTENT_STATUS.IN_PROGRESS
      ? "content-row is-current"
      : "content-row";
  const metaParts = [typeLabel[item.mode], item.duration].filter(Boolean);
  const orderLabel = String(item.order ?? "").padStart(2, "0");

  return (
    <Link
      className={rowClassName}
      to={buildLearningRoute(courseId, item)}
      aria-label={`Open ${item.title}`}
    >
      <div className="content-row-main">
        <span className="content-order">{orderLabel}</span>
        <div className="content-copy">
          {/* Both lessons and quizzes get a compact badge for symmetry and quicker scanning. */}
          <span className={`content-type-badge is-${item.mode}`}>
            {typeLabel[item.mode]}
          </span>
          <span className="content-title">{item.title}</span>
          <span className="content-meta">{metaParts.join(" | ")}</span>
        </div>
      </div>
      <StatusIndicator status={item.status} />
    </Link>
  );
}
