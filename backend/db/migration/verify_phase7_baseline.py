"""Rehearse imported-user quiz writes in a guarded disposable database only."""
import os
import re

from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.config.security import create_access_token
from backend.db.migration.verify_phase5_baseline import main as verify_source
from backend.db.migration.verify_phase6_baseline import exercise_writes as exercise_phase6
from backend.db.mongo.quiz_schema import upgrade_quiz_receipts
from backend.main import app
from backend.modules.courses.mongo_quiz import badge_for_points
from backend.modules.courses.mongo_service import MongoCourseService


def snapshot(database):
    return {name: list(database[name].find().sort("_id", 1)) for name in database.list_collection_names()}


def exercise_writes(database, source):
    if not re.fullmatch(r"learnova_test_[0-9a-f]{32}", database.name):
        raise RuntimeError("Phase 7 rehearsal requires a generated disposable target.")
    if any(os.environ.get(key) != "mongo" for key in ("AUTH_STORAGE", "ADMIN_STORAGE", "COURSES_STORAGE")):
        raise RuntimeError("All converted stores must select MongoDB for the quiz rehearsal.")
    prior_phase = exercise_phase6(database, source)
    choices = []
    for quiz in database.quizzes.find():
        if not quiz["questions"] or any(not question["options"] or not any(option["is_correct"] for option in question["options"])
                                        for question in quiz["questions"]):
            continue
        course = database.courses.find_one({"_id": quiz["course_id"], "is_published": True})
        if course is None: continue
        for member in database.enrollments.find({"course_id": course["_id"], "payment_status": {"$in": ["paid", "not_required"]}}):
            latest = database.quiz_attempts.find_one({"quiz_id": quiz["_id"], "user_id": member["user_id"]},
                                                    sort=[("attempt_number", -1)])
            remaining = quiz["max_attempts"] - (latest["attempt_number"] if latest else 0)
            if remaining > 0: choices.append((remaining, quiz, course, member))
    if not choices:
        raise RuntimeError("No eligible imported identity with a ready quiz and a remaining attempt exists.")
    remaining, quiz, course, member = max(choices, key=lambda choice: choice[0])
    user_row = database.users.find_one({"_id": member["user_id"]})
    user = {"id": user_row["_id"], "name": user_row["name"], "email": user_row["email"], "role": user_row["role"]}
    course_id, user_id = course["_id"], user["id"]
    content = database.course_content.find_one({"_id": quiz["content_id"]})
    prior_lessons = list(database.course_content.find({"course_id": course_id, "content_mode": {"$ne": "quiz"},
                                                      "display_order": {"$lt": content["display_order"]}}))
    changed_content_ids = {row["_id"] for row in prior_lessons} | {content["_id"]}
    answers = [{"questionId": question["id"], "selectedOptionIndexes": [index for index, option in
                enumerate(sorted(question["options"], key=lambda option: option["display_order"])) if option["is_correct"]]}
               for question in sorted(quiz["questions"], key=lambda question: question["display_order"])]
    before = snapshot(database)
    original_balance = database.learner_points.find_one({"user_id": user_id})
    original_total = original_balance["total_points"] if original_balance else 0
    original_attempt_ids = {row["_id"] for row in before["quiz_attempts"]}
    original_event_ids = {row["_id"] for row in before["point_events"]}
    token = create_access_token({"sub": user_id, "email": user["email"], "role": user["role"]})
    service = MongoCourseService(database)
    with TestClient(app) as client:
        if app.state.courses_storage != "mongo" or app.state.mongo_settings.database != database.name:
            raise RuntimeError("The quiz rehearsal app is not using the disposable target.")
        client.headers.update({"Authorization": "Bearer " + token})
        for lesson in prior_lessons:
            response = client.post(f"/courses/{course['slug']}/content/{lesson['slug']}/progress", json={"status": "completed", "lastPosition": 100})
            if response.status_code != 200: raise RuntimeError("Could not complete the imported quiz's prerequisites.")
        first = service.submit_quiz_attempt(course["slug"], content["slug"], user, answers, submission_key="phase7-source-first")
        results = [first]
        if remaining >= 2:
            response = client.post(f"/courses/{course['slug']}/quizzes/{content['slug']}/attempts", json={"answers": answers})
            if response.status_code != 200: raise RuntimeError("Imported user's second quiz submission failed.")
            results.append(response.json())
        replay_before = snapshot(database)
        if service.submit_quiz_attempt(course["slug"], content["slug"], user, list(reversed(answers)),
                                       submission_key="phase7-source-first") != first:
            raise RuntimeError("A keyed retry did not return its original result.")
        if snapshot(database) != replay_before: raise RuntimeError("A keyed retry mutated quiz/reward data.")
        modified = [{**answer, "selectedOptionIndexes": list(answer["selectedOptionIndexes"])} for answer in answers]
        modified[0]["selectedOptionIndexes"] = [999999]
        try:
            service.submit_quiz_attempt(course["slug"], content["slug"], user, modified, submission_key="phase7-source-first")
        except HTTPException as error:
            if error.status_code != 409: raise RuntimeError("Key reuse returned an unexpected status.") from None
        else: raise RuntimeError("Key reuse with changed answers was accepted.")
        if snapshot(database) != replay_before: raise RuntimeError("Rejected key reuse mutated data.")
        detail = client.get(f"/courses/{course['slug']}")
        player = client.get(f"/courses/{course['slug']}/quizzes/{content['slug']}")
        catalog = client.get("/courses")
        if any(response.status_code != 200 for response in (detail, player, catalog)):
            raise RuntimeError("Imported learner reads failed after quiz submission.")
        if player.json()["contentItem"]["status"] != "completed": raise RuntimeError("Quiz completion is not visible.")
        content_ids = [row["_id"] for row in database.course_content.find({"course_id": course_id}, {"_id": 1})]
        completed = database.content_progress.count_documents({"course_id": course_id, "user_id": user_id,
            "content_id": {"$in": content_ids}, "status": "completed"})
        expected_progress = {"completionPercentage": round(completed / max(len(content_ids), 1) * 100, 2),
            "totalCount": len(content_ids), "completedCount": completed, "incompleteCount": len(content_ids) - completed}
        if detail.json()["progress"] != expected_progress: raise RuntimeError("Quiz and course detail progress disagree.")
        balance = database.learner_points.find_one({"user_id": user_id})
        total = original_total + sum(result["pointsEarned"] for result in results)
        if balance["total_points"] != total or balance["current_badge"] != badge_for_points(total):
            raise RuntimeError("Quiz rewards changed the imported balance incorrectly.")
        if catalog.json()["profile"]["totalPoints"] != total: raise RuntimeError("Profile points do not reflect quiz rewards.")
        if original_balance and balance["_id"] != original_balance["_id"]: raise RuntimeError("Imported points identity changed.")
    new_attempts = list(database.quiz_attempts.find({"_id": {"$nin": list(original_attempt_ids)}}))
    new_events = list(database.point_events.find({"_id": {"$nin": list(original_event_ids)}}))
    if len(new_attempts) != len(results) or len(new_events) != len(results):
        raise RuntimeError("Quiz attempts and reward events are not one-to-one.")
    if {row["attempt_id"] for row in new_events} != {row["_id"] for row in new_attempts}:
        raise RuntimeError("Reward events do not reference their immutable attempts.")
    for row in new_attempts:
        if row["quiz_version"] != quiz["version"] or row["score"] != 100.0 or "result_snapshot" not in row:
            raise RuntimeError("New attempt scoring/version/receipt metadata is incomplete.")
    query = {"course_id": course_id, "user_id": user_id}
    for name, original in before.items():
        actual = list(database[name].find().sort("_id", 1))
        if name == "quiz_attempts": actual = [row for row in actual if row["_id"] in original_attempt_ids]
        elif name == "point_events": actual = [row for row in actual if row["_id"] in original_event_ids]
        elif name == "content_progress":
            for row in original:
                if row["content_id"] in changed_content_ids and row["user_id"] == user_id:
                    current = database.content_progress.find_one({"content_id": row["content_id"], "user_id": user_id})
                    if not current or current["_id"] != row["_id"]: raise RuntimeError("Imported progress identity changed.")
            original = [row for row in original if not (row["user_id"] == user_id and row["content_id"] in changed_content_ids)]
            actual = [row for row in actual if not (row["user_id"] == user_id and row["content_id"] in changed_content_ids)]
        elif name == "course_progress":
            previous = next((row for row in original if all(row[key] == value for key, value in query.items())), None)
            current = database.course_progress.find_one(query)
            if previous and any(current.get(key) != previous.get(key) for key in ("_id", "started_at")):
                raise RuntimeError("Imported summary identity/start time changed during quiz submission.")
            original = [row for row in original if not all(row[key] == value for key, value in query.items())]
            actual = [row for row in actual if not all(row[key] == value for key, value in query.items())]
        elif name == "learner_points":
            original = [row for row in original if row["user_id"] != user_id]
            actual = [row for row in actual if row["user_id"] != user_id]
        elif name == "quiz_attempt_counters":
            original = [row for row in original if not (row["quiz_id"] == quiz["_id"] and row["user_id"] == user_id)]
            actual = [row for row in actual if not (row["quiz_id"] == quiz["_id"] and row["user_id"] == user_id)]
        elif name == "courses":
            original = [{key: value for key, value in row.items() if not (row["_id"] == course_id and key == "updated_at")} for row in original]
            actual = [{key: value for key, value in row.items() if not (row["_id"] == course_id and key == "updated_at")} for row in actual]
        if actual != original: raise RuntimeError("Quiz rehearsal changed unrelated records: " + name)
    return {"phase6": prior_phase, "quiz_submissions_exercised": len(results), "keyed_service_replays_exercised": 1,
        "key_reuse_conflict_verified": True, "new_rewards_linked_one_to_one": True,
        "imported_balance_and_access_preserved": True, "untargeted_records_unchanged": True,
        "source_historical_attempt_count": len(source["quiz_attempts"]), "post_write_learner_reads_verified": 3,
        "postgres_write_baseline_exercised": False, "http_retry_header_integration_pending": True}


if __name__ == "__main__":
    verify_source("phase7", exercise=exercise_writes, prepare=upgrade_quiz_receipts)
