"""Phase 7 real-server schema, scoring, retry, reward, and concurrency coverage."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from pymongo.errors import OperationFailure, WriteError
import pytest

from backend.db.mongo.init_db import SchemaDriftError, initialize_database, load_spec
from backend.db.mongo.quiz_schema import EXTENSION_ID, load_extension, require_quiz_receipts, upgrade_quiz_receipts
from backend.db.mongo.seed import fixture_documents, fixture_id
from backend.db.mongo.transactions import lock_course
from backend.modules.courses.mongo_quiz import (
    allocate_attempt, award_points, badge_for_points, normalize_answers, quiz_fingerprint, reward_for_attempt, score_answers,
)
from backend.modules.admin.mongo_service import MongoAdminService
from backend.tests.test_mongo_admin import quiz_payload
from backend.tests.test_mongo_courses import courses, learner, learner_http, enrollment, complete_lesson
from backend.tests.test_mongo_progress_reviews import snapshot, synchronize


def legacy_attempt(number=1, user=None):
    return {"_id": str(uuid4()), "schema_version": 1, "quiz_id": fixture_id("quiz"),
        "user_id": user or fixture_id("learner"), "attempt_number": number, "score": 50.0,
        "points_earned": 10, "submitted_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "answers": [], "quiz_version": None}


def test_quiz_schema_extension_preserves_v1_history_and_repeats(database):
    database.quiz_attempts.insert_one(legacy_attempt())
    before = snapshot(database)
    first = upgrade_quiz_receipts(database)
    require_quiz_receipts(database)
    assert first["domain_records_rewritten"] == 0
    assert first["base_checksum"] == "8cc0040d337068cebb97642976d6b63f4a9f1d0927a5fafb6f36a19a335ffef8"
    after = snapshot(database)
    assert all(before[name] == after[name] for name in before if name != "schema_migrations")
    assert len(after["schema_migrations"]) == 2
    assert upgrade_quiz_receipts(database) == first
    assert snapshot(database) == after
    assert initialize_database(database)["named_indexes"] == 28
    assert snapshot(database) == after


def test_quiz_schema_readiness_rejects_v1_and_changed_extension(database):
    with pytest.raises(HTTPException) as failure: require_quiz_receipts(database)
    assert failure.value.status_code == 503
    upgrade_quiz_receipts(database)
    database.schema_migrations.update_one({"_id": EXTENSION_ID}, {"$set": {"checksum": "different"}})
    with pytest.raises(HTTPException): require_quiz_receipts(database)
    with pytest.raises(SchemaDriftError): initialize_database(database)
    with pytest.raises(SchemaDriftError): upgrade_quiz_receipts(database)


@pytest.mark.parametrize("drift", ["index", "collection", "ledger", "validator"])
def test_quiz_schema_preflight_stops_before_mutation(database, drift):
    if drift == "index": database.reviews.create_index("rating", name="unexpected")
    elif drift == "collection": database.create_collection("unmanaged")
    elif drift == "ledger": database.schema_migrations.update_one({}, {"$set": {"checksum": "wrong"}})
    else: database.command({"collMod": "reviews", "validationLevel": "moderate"})
    before = snapshot(database)
    options = list(database.list_collections())
    with pytest.raises(SchemaDriftError): upgrade_quiz_receipts(database)
    assert snapshot(database) == before and list(database.list_collections()) == options


def test_quiz_schema_recovers_exact_interruption_after_ddl(database, monkeypatch):
    from pymongo.synchronous.collection import Collection
    original = Collection.update_one
    def fail(self, query, *args, **kwargs):
        if self.name == "schema_migrations" and query.get("_id") == EXTENSION_ID:
            raise RuntimeError("Injected ledger failure after DDL")
        return original(self, query, *args, **kwargs)
    before = snapshot(database)
    with monkeypatch.context() as patch:
        patch.setattr(Collection, "update_one", fail)
        with pytest.raises(RuntimeError): upgrade_quiz_receipts(database)
    assert snapshot(database) == before
    with pytest.raises(SchemaDriftError): initialize_database(database)
    assert upgrade_quiz_receipts(database)["domain_records_rewritten"] == 0
    require_quiz_receipts(database)


def test_receipt_validator_accepts_legacy_and_rejects_partial_result(database):
    upgrade_quiz_receipts(database)
    database.quiz_attempts.insert_one(legacy_attempt())
    invalid = {**legacy_attempt(2), "result_snapshot": {"attemptNumber": 2}}
    with pytest.raises(WriteError) as failure: database.quiz_attempts.insert_one(invalid)
    assert failure.value.code == 121


@pytest.mark.parametrize("total,badge", [(0, "Newbie"), (20, "Newbie"), (21, "Explorer"),
    (40, "Explorer"), (41, "Achiever"), (60, "Achiever"), (61, "Specialist"),
    (80, "Specialist"), (81, "Expert"), (100, "Expert"), (101, "Master"), (1000, "Master")])
def test_badge_boundaries(total, badge):
    assert badge_for_points(total) == badge


@pytest.mark.parametrize("answers", [None, [None], [{}], [{"questionId": "q", "selectedOptionIndexes": []}],
    [{"questionId": "q", "selectedOptionIndexes": [-1]}], [{"questionId": "q", "selectedOptionIndexes": [True]}],
    [{"questionId": "q", "selectedOptionIndexes": [0, 0]}],
    [{"questionId": "q", "selectedOptionIndexes": [0]}, {"questionId": "q", "selectedOptionIndexes": [1]}]])
def test_answer_normalization_rejects_invalid_or_duplicate_input(answers):
    with pytest.raises(HTTPException) as failure: normalize_answers(answers)
    assert failure.value.status_code == 400


@pytest.mark.parametrize("selection,expected", [([0, 2], 100.0), ([0], 0.0), ([2], 0.0), ([0, 1, 2], 0.0)])
def test_exact_set_scoring_with_ordered_options(selection, expected):
    quiz = deepcopy(fixture_documents()["quizzes"][0])
    question = quiz["questions"][0]
    question["options"].append({"id": str(uuid4()), "option_text": "Also yes", "display_order": 3, "is_correct": True})
    question["options"].reverse()
    submitted = normalize_answers([{"questionId": question["id"], "selectedOptionIndexes": selection}])
    ids = {(question["id"], index): str(uuid4()) for index in selection}
    score, rows = score_answers(quiz, submitted, ids)
    assert score == expected and all(row["is_correct"] == (expected == 100) for row in rows)
    assert len(rows) == len(selection)


def test_quiz_fingerprint_identifies_scoring_definition():
    quiz = fixture_documents()["quizzes"][0]
    original = quiz_fingerprint(quiz)
    quiz["title"] = "Cosmetic title"
    assert quiz_fingerprint(quiz) == original
    quiz["questions"][0]["options"][0]["is_correct"] = False
    assert quiz_fingerprint(quiz) != original


def test_reward_fallback_retains_sql_selection():
    quiz = {"reward_rules": [{"attempt_number": number, "points_awarded": points}
                            for number, points in ((1, 40), (2, 20), (3, 10), (4, 5))]}
    assert [reward_for_attempt(quiz, number) for number in range(1, 7)] == [40, 20, 10, 5, 5, 5]
    quiz["reward_rules"] = [quiz["reward_rules"][0], quiz["reward_rules"][2]]
    assert reward_for_attempt(quiz, 2) == 10
    assert reward_for_attempt({"reward_rules": []}, 1) == 0


@pytest.mark.parametrize("counter_value", [None, 0, 5])
def test_counter_allocation_uses_historical_maximum_not_count(database, courses, counter_value):
    quiz = database.quizzes.find_one()
    database.quizzes.update_one({}, {"$set": {"max_attempts": 8}})
    quiz["max_attempts"] = 8
    for number in (1, 5): database.quiz_attempts.insert_one(legacy_attempt(number))
    stamp = datetime.now(timezone.utc)
    if counter_value is not None:
        database.quiz_attempt_counters.insert_one({"_id": str(uuid4()), "schema_version": 1,
            "quiz_id": quiz["_id"], "user_id": fixture_id("learner"), "attempts_used": counter_value, "updated_at": stamp})
    def allocate(session):
        lock_course(database, quiz["course_id"], session)
        return allocate_attempt(database, quiz, fixture_id("learner"), session, stamp=stamp, identifier=str(uuid4()))
    assert courses._transaction(allocate) == 6
    assert database.quiz_attempt_counters.find_one()["attempts_used"] == 6
    assert database.quiz_attempts.count_documents({}) == 2


def test_counter_maximum_guard_rolls_back_initialization(database, courses):
    quiz = database.quizzes.find_one()
    database.quiz_attempts.insert_one(legacy_attempt(quiz["max_attempts"]))
    before = snapshot(database)
    def allocate(session):
        lock_course(database, quiz["course_id"], session)
        return allocate_attempt(database, quiz, fixture_id("learner"), session,
            stamp=datetime.now(timezone.utc), identifier=str(uuid4()))
    with pytest.raises(HTTPException) as failure: courses._transaction(allocate)
    assert failure.value.status_code == 400 and snapshot(database) == before


def test_first_and_existing_balance_badges_follow_resulting_total(database, courses):
    identifier = str(uuid4())
    def award(points):
        return courses._transaction(lambda session: award_points(database, fixture_id("learner"), points, session,
            stamp=datetime.now(timezone.utc), identifier=identifier))
    assert award(41)["current_badge"] == "Achiever"
    assert award(40)["current_badge"] == "Expert"
    assert award(20)["current_badge"] == "Master"
    assert database.learner_points.find_one()["_id"] == identifier


@pytest.fixture
def quiz_ready(database):
    upgrade_quiz_receipts(database)
    enrollment(database)
    for mode in ("video", "document", "image"): complete_lesson(database, mode)
    return database.quizzes.find_one()


def answers_for(quiz, index=0):
    return [{"questionId": question["id"], "selectedOptionIndexes": [index]} for question in quiz["questions"]]


def submit(courses, learner, quiz, *, key=None, answers=None):
    return courses.submit_quiz_attempt("demo-open", "demo-quiz", learner,
        answers_for(quiz) if answers is None else answers, submission_key=key)


@pytest.mark.parametrize("problem", ["empty", "no_options", "one_option", "blank_prompt",
                                      "blank_option", "no_correct_option", "partial_definition"])
def test_unready_quiz_rejected_without_mutating_draft_or_learning_state(quiz_ready, learner_http, database, problem):
    questions = deepcopy(quiz_ready["questions"])
    if problem == "empty": questions = []
    elif problem == "no_options": questions[0]["options"] = []
    elif problem == "one_option": questions[0]["options"] = questions[0]["options"][:1]
    elif problem == "blank_prompt": questions[0]["question_text"] = "   "
    elif problem == "blank_option": questions[0]["options"][0]["option_text"] = "   "
    elif problem == "no_correct_option":
        for option in questions[0]["options"]: option["is_correct"] = False
    else:
        draft = deepcopy(questions[0])
        draft.update(id=str(uuid4()), display_order=2, options=[])
        questions.append(draft)
    database.quizzes.update_one({"_id": quiz_ready["_id"]}, {"$set": {"questions": questions}})
    before = snapshot(database)
    # Empty answers also ensure an empty quiz cannot earn rewards. For the mixed
    # definition, submit only the ready question that SQL's inner join would expose.
    answers = answers_for(quiz_ready) if problem == "partial_definition" else []
    response = learner_http.post("/courses/demo-open/quizzes/demo-quiz/attempts", json={"answers": answers})
    assert response.status_code == 409
    assert response.json()["detail"] == "This quiz is not ready for submission. Please contact your instructor."
    assert snapshot(database) == before
    # Completing the definition makes it submittable without any cleanup/import.
    database.quizzes.update_one({"_id": quiz_ready["_id"]}, {"$set": {"questions": quiz_ready["questions"]}})
    response = learner_http.post("/courses/demo-open/quizzes/demo-quiz/attempts", json={"answers": answers_for(quiz_ready)})
    assert response.status_code == 200 and response.json()["attemptNumber"] == 1


def test_quiz_submission_api_commits_all_side_effects(quiz_ready, learner_http, database):
    response = learner_http.post("/courses/demo-open/quizzes/demo-quiz/attempts", json={"answers": answers_for(quiz_ready)})
    assert response.status_code == 200
    assert response.json() == {"attemptNumber": 1, "score": 100.0, "pointsEarned": 10, "totalPoints": 10,
        "currentBadge": "Newbie", "nextTarget": 100, "message": "Reach the next rank to gain more points."}
    attempt = database.quiz_attempts.find_one()
    event = database.point_events.find_one()
    assert attempt["result_snapshot"] == response.json() and attempt["quiz_version"] == 1
    assert attempt["quiz_fingerprint"] == quiz_fingerprint(quiz_ready) and attempt["question_count"] == 1
    assert "submission_key" not in attempt
    assert event["attempt_id"] == attempt["_id"] and event["points_delta"] == 10
    assert attempt["answers"][0]["selected_option_id"] == fixture_id("option-yes")
    assert attempt["answers"][0]["is_correct"]
    assert database.quiz_attempt_counters.find_one()["attempts_used"] == 1
    progress = database.content_progress.find_one({"content_id": fixture_id("content-quiz")})
    assert progress["status"] == "completed" and progress["last_position"] == 100
    summary = database.course_progress.find_one()
    assert summary["completion_percentage"] == 100.0 and summary["completed_count"] == 4
    assert summary["status"] == "completed" and summary["current_content_id"] == fixture_id("content-quiz")
    assert learner_http.get("/courses").json()["profile"]["totalPoints"] == 10


def test_optional_http_key_replays_original_receipt_and_rejects_changed_payload(quiz_ready, learner_http, database):
    path = "/courses/demo-open/quizzes/demo-quiz/attempts"
    first = learner_http.post(path, json={"answers": answers_for(quiz_ready)}, headers={"Idempotency-Key": "first"})
    assert first.status_code == 200
    second = learner_http.post(path, json={"answers": answers_for(quiz_ready)}, headers={"Idempotency-Key": "second"})
    assert second.status_code == 200 and second.json()["attemptNumber"] == 2
    before = snapshot(database)
    replay = learner_http.post(path, json={"answers": answers_for(quiz_ready)}, headers={"Idempotency-Key": "first"})
    assert replay.status_code == 200 and replay.json() == first.json()
    conflict = learner_http.post(path, json={"answers": answers_for(quiz_ready, 1)}, headers={"Idempotency-Key": "first"})
    assert conflict.status_code == 409 and snapshot(database) == before
    assert database.quiz_attempts.count_documents({}) == database.point_events.count_documents({}) == 2


@pytest.mark.parametrize("key", ["", "space key", "x" * 129])
def test_invalid_http_key_creates_no_attempt(quiz_ready, learner_http, database, key):
    before = snapshot(database)
    response = learner_http.post("/courses/demo-open/quizzes/demo-quiz/attempts",
        json={"answers": answers_for(quiz_ready)}, headers={"Idempotency-Key": key})
    assert response.status_code == 422 and snapshot(database) == before


def test_quiz_retry_capability_and_cors(learner_http, monkeypatch):
    assert learner_http.get("/courses/quiz-submissions/capabilities").json() == {"idempotencyKeySupported": True}
    preflight = learner_http.options("/courses/demo-open/quizzes/demo-quiz/attempts", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type,idempotency-key"})
    assert preflight.status_code == 200
    assert "idempotency-key" in preflight.headers["access-control-allow-headers"].lower()
    monkeypatch.setattr(learner_http.app.state, "courses_storage", "postgres")
    assert learner_http.get("/courses/quiz-submissions/capabilities").json() == {"idempotencyKeySupported": False}


def test_postgres_mode_does_not_silently_ignore_retry_key(learner_http, monkeypatch):
    from backend.modules.courses.storage import get_course_service
    class LegacyCourses:
        def submit_quiz_attempt(self, *args):
            return {"legacy": True}
    monkeypatch.setattr(learner_http.app.state, "courses_storage", "postgres")
    learner_http.app.dependency_overrides[get_course_service] = lambda: LegacyCourses()
    try:
        path = "/courses/demo-open/quizzes/demo-quiz/attempts"
        response = learner_http.post(path, json={"answers": []}, headers={"Idempotency-Key": "retry"})
        assert response.status_code == 409
        response = learner_http.post(path, json={"answers": []})
        assert response.status_code == 200 and response.json() == {"legacy": True}
    finally:
        learner_http.app.dependency_overrides.pop(get_course_service, None)


def test_wrong_answer_still_receives_configured_reward_and_completes(quiz_ready, courses, database, learner):
    result = submit(courses, learner, quiz_ready, answers=answers_for(quiz_ready, 1))
    assert result["score"] == 0.0 and result["pointsEarned"] == 10
    assert not database.quiz_attempts.find_one()["answers"][0]["is_correct"]
    assert database.course_progress.find_one()["status"] == "completed"


def test_attempt_limit_and_unkeyed_deliberate_attempts(quiz_ready, courses, database, learner):
    first, second = submit(courses, learner, quiz_ready), submit(courses, learner, quiz_ready)
    assert first["attemptNumber"] == 1 and second["attemptNumber"] == 2 and second["totalPoints"] == 20
    before = snapshot(database)
    with pytest.raises(HTTPException) as failure: submit(courses, learner, quiz_ready)
    assert failure.value.status_code == 400 and snapshot(database) == before
    assert database.point_events.count_documents({}) == database.quiz_attempts.count_documents({}) == 2


def test_first_large_reward_computes_badge_instead_of_sql_insert_default(quiz_ready, courses, database, learner):
    database.quizzes.update_one({}, {"$set": {"reward_rules.0.points_awarded": 101}})
    assert submit(courses, learner, quiz_ready)["currentBadge"] == "Master"


@pytest.mark.parametrize("total,badge", [(20, "Newbie"), (21, "Explorer"), (40, "Explorer"), (41, "Achiever"),
    (60, "Achiever"), (61, "Specialist"), (80, "Specialist"), (81, "Expert"), (100, "Expert"), (101, "Master")])
def test_submission_updates_balance_and_badge_boundaries(quiz_ready, courses, database, learner, total, badge):
    identifier = str(uuid4())
    database.learner_points.insert_one({"_id": identifier, "schema_version": 1, "user_id": learner["id"],
        "total_points": total - 10, "current_badge": "Newbie", "updated_at": datetime.now(timezone.utc)})
    result = submit(courses, learner, quiz_ready)
    assert result["totalPoints"] == total and result["currentBadge"] == badge
    assert database.learner_points.find_one()["_id"] == identifier


@pytest.mark.parametrize("problem,expected", [("missing", 400), ("unknown", 400), ("extra", 400),
    ("duplicate_question", 400), ("duplicate_selection", 400), ("out_of_range", 400),
    ("negative", 422), ("empty_selection", 422)])
def test_invalid_quiz_answers_do_not_mutate(quiz_ready, learner_http, database, problem, expected):
    answers = answers_for(quiz_ready)
    if problem == "missing": answers = []
    elif problem == "unknown": answers[0]["questionId"] = str(uuid4())
    elif problem == "extra": answers.append({"questionId": str(uuid4()), "selectedOptionIndexes": [0]})
    elif problem == "duplicate_question": answers.append(deepcopy(answers[0]))
    else: answers[0]["selectedOptionIndexes"] = {"duplicate_selection": [0, 0], "out_of_range": [2],
                                               "negative": [-1], "empty_selection": []}[problem]
    before = snapshot(database)
    response = learner_http.post("/courses/demo-open/quizzes/demo-quiz/attempts", json={"answers": answers})
    assert response.status_code == expected and snapshot(database) == before


@pytest.mark.parametrize("payment,expected", [(None, 403), ("pending", 403), ("paid", 200), ("not_required", 200)])
def test_quiz_enrollment_access(quiz_ready, learner_http, database, payment, expected):
    database.enrollments.delete_many({})
    if payment: enrollment(database, payment=payment)
    before = snapshot(database)
    response = learner_http.post("/courses/demo-open/quizzes/demo-quiz/attempts", json={"answers": answers_for(quiz_ready)})
    assert response.status_code == expected
    if expected != 200: assert snapshot(database) == before
    assert database.payment_orders.count_documents({}) == 0


@pytest.mark.parametrize("course,content", [("missing", "demo-quiz"), ("demo-payment", "demo-quiz"),
    ("demo-open", "missing"), ("demo-open", "demo-video")])
def test_quiz_scoped_course_content_and_missing(quiz_ready, learner_http, database, course, content):
    enrollment(database, "payment", "paid")
    before = snapshot(database)
    response = learner_http.post(f"/courses/{course}/quizzes/{content}/attempts", json={"answers": answers_for(quiz_ready)})
    assert response.status_code == 404 and snapshot(database) == before


def test_unpublished_quiz_course_and_missing_auth_user(quiz_ready, learner_http, database, courses, learner):
    database.courses.update_one({"slug": "demo-open"}, {"$set": {"is_published": False}})
    assert learner_http.post("/courses/demo-open/quizzes/demo-quiz/attempts", json={"answers": answers_for(quiz_ready)}).status_code == 404
    learner_http.headers.clear()
    assert learner_http.post("/courses/demo-open/quizzes/demo-quiz/attempts", json={"answers": answers_for(quiz_ready)}).status_code == 401
    database.courses.update_one({"slug": "demo-open"}, {"$set": {"is_published": True}})
    learner["id"] = str(uuid4())
    with pytest.raises(HTTPException) as failure: submit(courses, learner, quiz_ready)
    assert failure.value.status_code == 404 and database.quiz_attempts.count_documents({}) == 0


def test_quiz_requires_own_preceding_lessons(quiz_ready, courses, database, learner):
    database.content_progress.delete_many({})
    for mode in ("video", "document", "image"): complete_lesson(database, mode, user=fixture_id("instructor"))
    before = snapshot(database)
    with pytest.raises(HTTPException) as failure: submit(courses, learner, quiz_ready)
    assert failure.value.status_code == 403 and snapshot(database) == before


def test_quiz_requires_explicit_schema_migration(learner_http, database, monkeypatch):
    def fail(): raise AssertionError("MongoDB quiz submission must never fall back to PostgreSQL")
    monkeypatch.setattr("backend.modules.courses.service.connect", fail)
    before = snapshot(database)
    response = learner_http.post("/courses/demo-open/quizzes/demo-quiz/attempts", json={"answers": []},
                                 headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 503 and snapshot(database) == before
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_same_key_returns_original_result_after_later_attempt(quiz_ready, courses, database, learner):
    first = submit(courses, learner, quiz_ready, key="first")
    second = submit(courses, learner, quiz_ready, key="second")
    assert second["totalPoints"] == 20
    before = snapshot(database)
    assert submit(courses, learner, quiz_ready, key="first") == first
    assert snapshot(database) == before


def test_key_reuse_with_different_answers_is_conflict(quiz_ready, courses, database, learner):
    submit(courses, learner, quiz_ready, key="same")
    before = snapshot(database)
    with pytest.raises(HTTPException) as failure:
        submit(courses, learner, quiz_ready, key="same", answers=answers_for(quiz_ready, 1))
    assert failure.value.status_code == 409 and snapshot(database) == before


@pytest.mark.parametrize("key", ["", "x" * 129, "has space", "line\nbreak", "nonascii-\u00e9"])
def test_invalid_submission_key_is_rejected(quiz_ready, courses, database, learner, key):
    before = snapshot(database)
    with pytest.raises(HTTPException) as failure: submit(courses, learner, quiz_ready, key=key)
    assert failure.value.status_code == 422 and snapshot(database) == before


def test_retry_survives_reopened_prerequisite_and_quiz_edit(quiz_ready, courses, database, learner):
    first = submit(courses, learner, quiz_ready, key="committed")
    database.content_progress.update_one({"content_id": fixture_id("content-video")}, {"$set": {"status": "in_progress"}})
    database.quizzes.update_one({}, {"$set": {"questions": [], "version": 2}})
    before = snapshot(database)
    assert submit(courses, learner, quiz_ready, key="committed") == first and snapshot(database) == before


def test_retry_still_requires_current_access(quiz_ready, courses, database, learner):
    submit(courses, learner, quiz_ready, key="committed")
    database.enrollments.update_one({}, {"$set": {"payment_status": "pending"}})
    before = snapshot(database)
    with pytest.raises(HTTPException) as failure: submit(courses, learner, quiz_ready, key="committed")
    assert failure.value.status_code == 403 and snapshot(database) == before


@pytest.mark.parametrize("counter_value", [None, 0, 5])
def test_submission_continues_imported_attempt_history(quiz_ready, courses, database, learner, counter_value):
    for number in (1, 5): database.quiz_attempts.insert_one(legacy_attempt(number))
    database.quizzes.update_one({}, {"$set": {"max_attempts": 8}})
    if counter_value is not None:
        database.quiz_attempt_counters.insert_one({"_id": str(uuid4()), "schema_version": 1,
            "quiz_id": quiz_ready["_id"], "user_id": learner["id"], "attempts_used": counter_value,
            "updated_at": datetime.now(timezone.utc)})
    originals = list(database.quiz_attempts.find().sort("_id", 1))
    result = submit(courses, learner, quiz_ready)
    assert result["attemptNumber"] == 6 and database.quiz_attempt_counters.find_one()["attempts_used"] == 6
    assert list(database.quiz_attempts.find({"attempt_number": {"$lt": 6}}).sort("_id", 1)) == originals


def test_same_key_concurrency_commits_one_attempt_reward(quiz_ready, courses, database, learner, monkeypatch):
    synchronize(monkeypatch, courses, courses)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: submit(courses, learner, quiz_ready, key="same"), (1, 2)))
    assert results[0] == results[1]
    assert database.quiz_attempts.count_documents({}) == database.point_events.count_documents({}) == 1
    assert database.learner_points.find_one()["total_points"] == 10
    assert database.quiz_attempt_counters.find_one()["attempts_used"] == 1


def test_concurrent_final_attempt_respects_limit(quiz_ready, courses, database, learner, monkeypatch):
    submit(courses, learner, quiz_ready, key="first")
    synchronize(monkeypatch, courses, courses)
    def attempt(key):
        try: return submit(courses, learner, quiz_ready, key=key)["attemptNumber"]
        except HTTPException as failure: return failure.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ("last-a", "last-b")))
    assert sorted(results) == [2, 400]
    assert database.quiz_attempts.count_documents({}) == database.point_events.count_documents({}) == 2
    assert database.learner_points.find_one()["total_points"] == 20


@pytest.mark.parametrize("stage", ["counter", "attempt", "content", "summary", "points", "receipt", "event"])
def test_failure_after_each_quiz_write_rolls_back_everything(quiz_ready, courses, database, learner, monkeypatch, stage):
    from pymongo.synchronous.collection import Collection
    before = snapshot(database)
    original_insert, original_update, original_allocate = Collection.insert_one, Collection.update_one, Collection.find_one_and_update
    def fail_if(current):
        if current == stage: raise HTTPException(409, "Injected post-write failure")
    def insert(self, *args, **kwargs):
        result = original_insert(self, *args, **kwargs)
        fail_if({"quiz_attempts": "attempt", "point_events": "event"}.get(self.name))
        return result
    def update(self, *args, **kwargs):
        result = original_update(self, *args, **kwargs)
        fail_if({"content_progress": "content", "course_progress": "summary", "learner_points": "points",
                 "quiz_attempts": "receipt"}.get(self.name))
        return result
    def allocate(self, *args, **kwargs):
        result = original_allocate(self, *args, **kwargs)
        if self.name == "quiz_attempt_counters": fail_if("counter")
        return result
    monkeypatch.setattr(Collection, "insert_one", insert)
    monkeypatch.setattr(Collection, "update_one", update)
    monkeypatch.setattr(Collection, "find_one_and_update", allocate)
    with pytest.raises(HTTPException): submit(courses, learner, quiz_ready, key="rollback")
    assert snapshot(database) == before


def test_quiz_retry_reuses_all_ids_after_actual_transient_error(quiz_ready, courses, database, learner, monkeypatch):
    from pymongo.synchronous.collection import Collection
    original, identities = Collection.insert_one, []
    def retry(self, document, *args, **kwargs):
        result = original(self, document, *args, **kwargs)
        if self.name == "point_events":
            session = kwargs["session"]
            attempt = database.quiz_attempts.find_one(session=session)
            identities.append((attempt["_id"], attempt["answers"][0]["id"], document["_id"],
                database.quiz_attempt_counters.find_one(session=session)["_id"],
                database.learner_points.find_one(session=session)["_id"], database.course_progress.find_one(session=session)["_id"]))
            if len(identities) == 1:
                raise OperationFailure("Injected transient error", 112, {"errorLabels": ["TransientTransactionError"]})
        return result
    monkeypatch.setattr(Collection, "insert_one", retry)
    assert submit(courses, learner, quiz_ready, key="retry")["attemptNumber"] == 1
    assert len(identities) == 2 and identities[0] == identities[1]
    assert database.quiz_attempts.count_documents({}) == database.point_events.count_documents({}) == 1


def test_quiz_api_never_connects_to_postgres(quiz_ready, learner_http, database, monkeypatch):
    def fail(): raise AssertionError("MongoDB quiz writes must not connect to PostgreSQL")
    for module in ("courses", "admin", "auth"):
        monkeypatch.setattr(f"backend.modules.{module}.service.connect", fail)
    assert learner_http.post("/courses/demo-open/quizzes/demo-quiz/attempts", json={"answers": answers_for(quiz_ready)}).status_code == 200


def test_multiple_question_rounding_and_canonical_retry(quiz_ready, courses, database, learner):
    question = deepcopy(quiz_ready["questions"][0])
    questions = [question]
    for order in (2, 3):
        clone = deepcopy(question)
        clone.update(id=str(uuid4()), display_order=order)
        clone["options"] = [{**option, "id": str(uuid4())} for option in clone["options"]]
        questions.append(clone)
    questions[0]["options"].append({"id": str(uuid4()), "option_text": "Also correct", "display_order": 3, "is_correct": True})
    database.quizzes.update_one({}, {"$set": {"questions": questions}})
    answers = [{"questionId": question["id"], "selectedOptionIndexes": indexes}
               for question, indexes in zip(questions, ([2, 0], [0], [1]))]
    first = submit(courses, learner, quiz_ready, key="canonical", answers=answers)
    assert first["score"] == 66.67
    before = snapshot(database)
    answers.reverse()
    answers[-1]["selectedOptionIndexes"].reverse()
    assert submit(courses, learner, quiz_ready, key="canonical", answers=answers) == first
    assert snapshot(database) == before
    assert database.quiz_attempts.find_one()["question_count"] == 3
    assert len(database.quiz_attempts.find_one()["answers"]) == 4


def test_key_is_scoped_to_quiz_and_user(quiz_ready, courses, database, learner):
    first = submit(courses, learner, quiz_ready, key="shared")
    other = database.users.find_one({"_id": fixture_id("instructor")})
    user = {"id": other["_id"], "name": other["name"]}
    enrollment(database, user=user["id"])
    for mode in ("video", "document", "image"): complete_lesson(database, mode, user=user["id"])
    assert submit(courses, user, quiz_ready, key="shared")["attemptNumber"] == 1
    created = MongoAdminService(database).create_course_quiz("demo-open", quiz_payload())
    quiz = database.quizzes.find_one({"_id": created["id"]})
    result = courses.submit_quiz_attempt("demo-open", created["contentSlug"], learner, answers_for(quiz), submission_key="shared")
    assert result["attemptNumber"] == 1 and result["totalPoints"] == first["totalPoints"] + 10
    assert database.quiz_attempts.count_documents({"submission_key": "shared"}) == 3


def test_legacy_key_without_receipt_cannot_guess_result(quiz_ready, courses, database, learner):
    from backend.modules.courses.mongo_quiz import digest
    row = {**legacy_attempt(), "submission_key": "legacy", "submission_fingerprint": digest(normalize_answers(answers_for(quiz_ready)))}
    database.quiz_attempts.insert_one(row)
    before = snapshot(database)
    with pytest.raises(HTTPException) as failure: submit(courses, learner, quiz_ready, key="legacy")
    assert failure.value.status_code == 409 and snapshot(database) == before


def test_quiz_edit_preserves_recorded_version_and_result(quiz_ready, courses, database, learner):
    first = submit(courses, learner, quiz_ready, key="version-one")
    stored = database.quiz_attempts.find_one()
    admin = MongoAdminService(database)
    payload = quiz_payload()
    detail = admin.get_quiz_detail(quiz_ready["_id"])
    payload.update(title="Demo quiz", questions=detail["questions"])
    payload["questions"][0]["choices"][0]["isCorrect"] = False
    payload["questions"][0]["choices"][1]["isCorrect"] = True
    admin.update_quiz_detail(quiz_ready["_id"], payload)
    second = submit(courses, learner, quiz_ready, key="version-two")
    assert second["score"] == 0.0 and second["pointsEarned"] == 8 and second["totalPoints"] == 18
    assert database.quiz_attempts.find_one({"_id": stored["_id"]}) == stored
    new = database.quiz_attempts.find_one({"attempt_number": 2})
    assert new["quiz_version"] == 2 and new["quiz_fingerprint"] != stored["quiz_fingerprint"]
    assert submit(courses, learner, quiz_ready, key="version-one") == first


def test_concurrent_quizzes_in_different_courses_keep_balance(quiz_ready, courses, database, learner, monkeypatch):
    enrollment(database, "payment", "paid")
    created = MongoAdminService(database).create_course_quiz("demo-payment", quiz_payload())
    other = database.quizzes.find_one({"_id": created["id"]})
    synchronize(monkeypatch, courses, courses)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(submit, courses, learner, quiz_ready, key="same")
        second = pool.submit(courses.submit_quiz_attempt, "demo-payment", created["contentSlug"], learner,
                             answers_for(other), submission_key="same")
        results = [first.result(), second.result()]
    assert sorted(result["totalPoints"] for result in results) == [10, 20]
    assert database.learner_points.count_documents({}) == 1
    assert database.learner_points.find_one()["total_points"] == 20
    assert database.quiz_attempts.count_documents({}) == database.point_events.count_documents({}) == 2


@pytest.mark.parametrize("target", ["course", "quiz"])
def test_quiz_submission_and_deletion_do_not_orphan(quiz_ready, courses, database, learner, monkeypatch, target):
    admin = MongoAdminService(database)
    synchronize(monkeypatch, courses, admin)
    def attempt():
        try: return submit(courses, learner, quiz_ready, key="racing")["attemptNumber"]
        except HTTPException as failure: return failure.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        writing = pool.submit(attempt)
        deletion = pool.submit(admin.delete_admin_course, "demo-open") if target == "course" else pool.submit(
            admin.delete_quiz_detail, quiz_ready["_id"])
        assert deletion.result()["deleted"] and writing.result() in (1, 404)
    assert database.quiz_attempts.count_documents({}) == database.quiz_attempt_counters.count_documents({}) == 0
    assert database.content_progress.count_documents({"content_id": fixture_id("content-quiz")}) == 0
    event = database.point_events.find_one()
    balance = database.learner_points.find_one()
    if event:
        assert event["quiz_id"] is None and "attempt_id" not in event and balance["total_points"] == 10
        if target == "course": assert event["course_id"] is None
    else: assert balance is None


def test_concurrent_reopening_and_quiz_preserve_lock_and_summary(quiz_ready, courses, database, learner, monkeypatch):
    synchronize(monkeypatch, courses, courses)
    def attempt():
        try: return submit(courses, learner, quiz_ready, key="racing")["attemptNumber"]
        except HTTPException as failure: return failure.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        quiz = pool.submit(attempt)
        lesson = pool.submit(courses.update_content_progress_for_user, "demo-open", "demo-video", learner,
                             status_value="in_progress", last_position=0)
        result = quiz.result()
        lesson.result()
    assert result in (1, 403)
    summary = database.course_progress.find_one()
    assert summary["completed_count"] == (3 if result == 1 else 2)
    assert summary["completion_percentage"] == (75.0 if result == 1 else 50.0)


def test_quiz_schema_rejection_rolls_back_all_stages(quiz_ready, courses, database, learner, monkeypatch):
    from pymongo.synchronous.collection import Collection
    before, original = snapshot(database), Collection.insert_one
    def invalid(self, document, *args, **kwargs):
        if self.name == "point_events": document["points_delta"] = "invalid"
        return original(self, document, *args, **kwargs)
    monkeypatch.setattr(Collection, "insert_one", invalid)
    with pytest.raises(HTTPException) as failure: submit(courses, learner, quiz_ready, key="invalid")
    assert failure.value.status_code == 422 and snapshot(database) == before
