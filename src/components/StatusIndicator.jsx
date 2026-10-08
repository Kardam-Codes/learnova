import { COURSE_CONTENT_STATUS } from "../../shared/types/common_types";

export default function StatusIndicator({ status }) {
  // Completed items get the blue check treatment from the sketch.
  if (status === COURSE_CONTENT_STATUS.COMPLETED) {
    return <span className="status-indicator is-completed" aria-label="Completed" />;
  }

  // In-progress items are highlighted separately from untouched content.
  if (status === COURSE_CONTENT_STATUS.IN_PROGRESS) {
    return <span className="status-indicator is-in-progress" aria-label="In progress" />;
  }

  // Default state is content not started by the learner.
  return <span className="status-indicator is-not-started" aria-label="Not started" />;
}
