"""Rehearse Phase 6 writes only in a disposable import; never mutate the SQL source."""
import os
import re
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.config.security import create_access_token
from backend.db.migration.verify_phase5_baseline import main as verify_source
from backend.main import app


def exercise_writes(database, source):
    if not re.fullmatch(r"learnova_test_[0-9a-f]{32}", database.name):
        raise RuntimeError("Phase 6 writes require a generated disposable database.")
    if any(os.environ.get(key) != "mongo" for key in ("AUTH_STORAGE", "ADMIN_STORAGE", "COURSES_STORAGE")):
        raise RuntimeError("All converted stores must explicitly select MongoDB for write rehearsal.")
    courses = {str(row["id"]): row for row in source["courses"]}
    users = {str(row["id"]): row for row in source["users"]}
    eligible = [row for row in source["course_attendees"] if row["payment_status"] in {"paid", "not_required"}
                and courses[str(row["course_id"])]["is_published"]
                and any(str(item["course_id"]) == str(row["course_id"]) and item["content_mode"] != "quiz"
                        for item in source["course_content"])]
    if not eligible:
        raise RuntimeError("The source has no eligible enrolled lesson fixture for rehearsal.")
    membership = eligible[0]
    course_id, user_id = str(membership["course_id"]), str(membership["user_id"])
    course, user = courses[course_id], users[user_id]
    token = create_access_token({"sub": user_id, "email": user["email"], "role": user["role"]})
    before = {name: list(database[name].find().sort("_id", 1)) for name in database.list_collection_names()}
    query = {"course_id": course_id, "user_id": user_id}
    previous = database.reviews.find_one(query)
    lesson = database.course_content.find_one({"course_id": course_id, "content_mode": {"$ne": "quiz"}})
    progress_query = {"content_id": lesson["_id"], "user_id": user_id}
    previous_content = database.content_progress.find_one(progress_query)
    previous_summary = database.course_progress.find_one(query)
    with TestClient(app) as client:
        if app.state.courses_storage != "mongo" or app.state.mongo_settings.database != database.name:
            raise RuntimeError("The application is not using this disposable target.")
        client.headers.update({"Authorization": "Bearer " + token})
        first = client.post(f"/courses/{course['slug']}/reviews", json={"rating": 4, "comment": "Phase 6 rehearsal review"})
        if first.status_code != 200:
            raise RuntimeError("Imported user's first review update failed.")
        created = database.reviews.find_one(query)
        second = client.post(f"/courses/{course['slug']}/reviews", json={"rating": 5, "comment": "Phase 6 rehearsal revised review"})
        if second.status_code != 200 or second.json()["learnerDraft"] != "Phase 6 rehearsal revised review":
            raise RuntimeError("Imported user's second review update failed.")
        updated = database.reviews.find_one(query)
        if updated["_id"] != created["_id"] or updated["created_at"] != created["created_at"]:
            raise RuntimeError("Review identity/creation date changed.")
        if previous and any(updated[key] != previous[key] for key in ("_id", "created_at")):
            raise RuntimeError("Existing source review identity/creation date changed.")
        rows = list(database.reviews.find({"course_id": course_id}))
        if second.json()["averageRating"] != round(sum(row["rating"] for row in rows) / len(rows), 1):
            raise RuntimeError("Review average differs from stored records.")
        path = f"/courses/{course['slug']}/content/{lesson['slug']}/progress"
        origin = datetime.now(timezone.utc).replace(microsecond=0)
        initial_content = initial_summary = None
        for index, status in enumerate(("in_progress", "completed", "completed", "in_progress", "completed")):
            stamp = origin + timedelta(days=index)
            with patch("backend.modules.courses.mongo_service.now", return_value=stamp):
                response = client.post(path, json={"status": status, "lastPosition": 0 if status == "in_progress" else 100})
            if response.status_code != 200 or response.json()["contentItem"]["status"] != status:
                raise RuntimeError("Imported user's progress update failed.")
            content = database.content_progress.find_one(progress_query)
            summary = database.course_progress.find_one(query)
            if index == 0:
                initial_content, initial_summary = content, summary
            for actual, initial, source_row, fields in (
                (content, initial_content, previous_content, ("_id",)),
                (summary, initial_summary, previous_summary, ("_id", "started_at")),
            ):
                if any(actual.get(key) != initial.get(key) for key in fields):
                    raise RuntimeError("Progress identity/start time changed between updates.")
                if source_row and any(actual.get(key) != source_row.get(key) for key in fields):
                    raise RuntimeError("Existing source progress identity/start time changed.")
            expected_completion = stamp if status == "completed" else None
            if content.get("completed_at") != expected_completion or content["last_position"] != (100 if status == "completed" else 0):
                raise RuntimeError("Progress completion lifecycle or position zero differs from SQL behavior.")
            identifiers = [row["_id"] for row in database.course_content.find({"course_id": course_id}, {"_id": 1})]
            progress = list(database.content_progress.find({**query, "content_id": {"$in": identifiers}}))
            total, completed = len(identifiers), sum(row["status"] == "completed" for row in progress)
            in_progress = any(row["status"] == "in_progress" for row in progress)
            expected_status = "completed" if completed == total else "in_progress" if completed or in_progress else "yet_to_start"
            expected = {"totalCount": total, "completedCount": completed, "incompleteCount": total - completed,
                        "completionPercentage": round(completed / max(total, 1) * 100, 2), "status": expected_status}
            if response.json()["progress"] != expected or summary["current_content_id"] != lesson["_id"]:
                raise RuntimeError("Stored lesson records and response summary disagree.")
            if any(summary[key] != expected[field] for key, field in (
                ("completed_count", "completedCount"), ("incomplete_count", "incompleteCount"),
                ("completion_percentage", "completionPercentage"), ("status", "status"))):
                raise RuntimeError("Stored course summary differs from current lesson records.")
            if summary.get("completed_at") != (stamp if expected_status == "completed" else None):
                raise RuntimeError("Course completion timestamp differs from SQL behavior.")
        detail = client.get(f"/courses/{course['slug']}")
        player = client.get(f"/courses/{course['slug']}/content/{lesson['slug']}")
        if detail.status_code != 200 or player.status_code != 200:
            raise RuntimeError("Imported learner reads failed after progress updates.")
        if detail.json()["progress"] != {key: value for key, value in expected.items() if key != "status"}:
            raise RuntimeError("Course detail differs from the updated summary.")
        if player.json()["contentItem"]["status"] != "completed":
            raise RuntimeError("Lesson player does not reflect completed progress.")
    # Only the selected learner's review/progress and the shared course timestamp may change.
    for name, original in before.items():
        actual = list(database[name].find().sort("_id", 1))
        if name in {"reviews", "course_progress"}:
            original = [row for row in original if not (row["course_id"] == course_id and row["user_id"] == user_id)]
            actual = [row for row in actual if not (row["course_id"] == course_id and row["user_id"] == user_id)]
        if name == "content_progress":
            original = [row for row in original if not (row["content_id"] == lesson["_id"] and row["user_id"] == user_id)]
            actual = [row for row in actual if not (row["content_id"] == lesson["_id"] and row["user_id"] == user_id)]
        if name == "courses":
            original = [{key: value for key, value in row.items() if not (row["_id"] == course_id and key == "updated_at")} for row in original]
            actual = [{key: value for key, value in row.items() if not (row["_id"] == course_id and key == "updated_at")} for row in actual]
        if actual != original:
            raise RuntimeError("A write rehearsal changed unrelated records: " + name)
    return {"review_upserts_exercised": 2, "review_identity_and_creation_date_preserved": True,
            "progress_updates_exercised": 5, "progress_identity_and_start_time_preserved": True,
            "completion_lifecycle_and_position_zero_verified": True, "summary_matches_current_content": True,
            "post_write_learner_reads_verified": 2,
            "untargeted_domain_records_unchanged": True, "postgres_write_baseline_exercised": False}


if __name__ == "__main__":
    verify_source("phase6", exercise=exercise_writes)
