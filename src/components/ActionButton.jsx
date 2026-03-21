/*
 * File: ActionButton.jsx
 * Owner: KARDAM
 * Purpose: Render the correct course action based on the learner's access state.
 * What it is: A small router-aware button used inside each course card.
 */
import { Link } from "react-router-dom";
import { COURSE_ACCESS_STATE } from "../../shared/types/common_types";

export default function ActionButton({ action, onClick }) {
  const actionClassName = `catalog-action-button is-${action.type}`;
  const label =
    action.type === COURSE_ACCESS_STATE.START ? "Start Course" : action.label;

  return (
    <Link className={actionClassName} to={action.to} onClick={onClick}>
      {label}
    </Link>
  );
}
