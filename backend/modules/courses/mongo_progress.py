"""Current-content progress totals; mutation callers hold the parent-course boundary."""
from fastapi import HTTPException


def load_progress_totals(database, course_id, user_id, session):
    # Current course content defines the denominator. Stale/orphan/foreign progress
    # cannot inflate completion or count another user's work toward this summary.
    identifiers = [row["_id"] for row in database.course_content.find({"course_id": course_id}, {"_id": 1}, session=session)]
    rows = list(database.content_progress.find({"course_id": course_id, "user_id": user_id,
        "content_id": {"$in": identifiers}}, {"status": 1}, session=session))
    total = len(identifiers)
    completed = sum(row["status"] == "completed" for row in rows)
    in_progress = sum(row["status"] == "in_progress" for row in rows)
    return {"totalCount": total, "completedCount": completed, "incompleteCount": max(total - completed, 0),
            "completionPercentage": round(completed / max(total, 1) * 100, 2), "inProgressCount": in_progress}


def recalculate_course_progress(database, course_id, user_id, current_content_id, session, *, stamp, identifier):
    if current_content_id is not None and database.course_content.find_one(
        {"_id": current_content_id, "course_id": course_id}, {"_id": 1}, session=session) is None:
        raise HTTPException(409, "Progress content reference does not belong to this course.")
    totals = load_progress_totals(database, course_id, user_id, session)
    # Preserve the inspected SQL calculation, including completed at 0% for no content.
    status = "completed" if totals["completedCount"] == totals["totalCount"] else (
        "in_progress" if totals["completedCount"] or totals["inProgressCount"] else "yet_to_start")
    database.course_progress.update_one({"course_id": course_id, "user_id": user_id}, {
        "$set": {"completion_percentage": totals["completionPercentage"], "completed_count": totals["completedCount"],
            "incomplete_count": totals["incompleteCount"], "current_content_id": current_content_id, "status": status,
            "completed_at": stamp if status == "completed" else None, "updated_at": stamp},
        "$setOnInsert": {"_id": identifier, "schema_version": 1, "started_at": stamp}}, upsert=True, session=session)
    return {key: value for key, value in {**totals, "status": status}.items() if key != "inProgressCount"}
