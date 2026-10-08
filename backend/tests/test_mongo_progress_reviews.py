"""Phase 6 real-server progress/review access, lifecycle, concurrency, and rollback."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import uuid4

from fastapi import HTTPException
from pymongo.errors import OperationFailure
import pytest

from backend.db.mongo.seed import fixture_id
from backend.modules.admin.mongo_service import MongoAdminService
from backend.db.mongo.transactions import lock_course
from backend.tests.test_mongo_auth import bearer
from backend.tests.test_mongo_courses import courses, learner, learner_http, enrollment, complete_lesson
from backend.tests.test_mongo_admin import lesson_payload


def snapshot(database):
    return {name: list(database[name].find().sort("_id", 1)) for name in database.list_collection_names()}


def synchronize(monkeypatch, *services):
    barrier = Barrier(len(services))
    seen = set()
    for service in services:
        if id(service) in seen: continue
        seen.add(id(service))
        original = service._transaction
        def synchronized(callback, run=original):
            barrier.wait(timeout=10)
            return run(callback)
        monkeypatch.setattr(service, "_transaction", synchronized)


def test_review_create_edit_retain_identity_and_creation_date(learner_http, database, monkeypatch):
    enrollment(database)
    stamp = datetime(2026, 2, 1, tzinfo=timezone.utc)
    monkeypatch.setattr("backend.modules.courses.mongo_service.now", lambda: stamp)
    first = learner_http.post("/courses/demo-open/reviews", json={"rating": 5, "comment": "First review"})
    assert first.status_code == 200 and first.json()["averageRating"] == 5 and first.json()["learnerDraft"] == "First review"
    before = database.reviews.find_one()
    stamp += timedelta(days=1)
    changed = learner_http.post("/courses/demo-open/reviews", json={"rating": 3, "comment": "Updated review"})
    assert changed.status_code == 200 and changed.json()["totalReviews"] == 1
    assert changed.json()["averageRating"] == 3 and changed.json()["learnerDraft"] == "Updated review"
    after = database.reviews.find_one()
    assert after["_id"] == before["_id"] and after["created_at"] == before["created_at"]
    assert after["updated_at"] == stamp
    assert learner_http.get("/courses/demo-open/reviews").json() == changed.json()
    assert learner_http.get("/courses/demo-open").json()["reviews"] == changed.json()


@pytest.mark.parametrize("payment,authorized", [(None, False), ("pending", False), ("not_required", True), ("paid", True)])
def test_review_enrollment_access(learner_http, database, payment, authorized):
    if payment: enrollment(database, payment=payment)
    before = snapshot(database)
    response = learner_http.post("/courses/demo-open/reviews", json={"rating": 4, "comment": "Review text"})
    assert response.status_code == (200 if authorized else 403)
    if not authorized: assert snapshot(database) == before


@pytest.mark.parametrize("slug", ["missing", "demo-open"])
def test_review_missing_or_unpublished_course(learner_http, database, slug):
    enrollment(database)
    database.courses.update_one({"slug": "demo-open"}, {"$set": {"is_published": False}})
    before = snapshot(database)
    assert learner_http.post(f"/courses/{slug}/reviews", json={"rating": 5, "comment": "Review text"}).status_code == 404
    assert snapshot(database) == before


@pytest.mark.parametrize("rating,comment", [(0, "Valid text"), (6, "Valid text"), (5, "Hi"), (5, "x" * 2001)])
def test_invalid_review_body_does_not_mutate(learner_http, database, rating, comment):
    enrollment(database)
    before = snapshot(database)
    assert learner_http.post("/courses/demo-open/reviews", json={"rating": rating, "comment": comment}).status_code == 422
    assert snapshot(database) == before


def test_review_requires_authentication_and_known_user(learner_http, database, courses, learner):
    learner_http.headers.clear()
    assert learner_http.post("/courses/demo-open/reviews", json={"rating": 5, "comment": "Review text"}).status_code == 401
    learner["id"] = str(uuid4())
    with pytest.raises(HTTPException) as failure:
        courses.submit_course_review("demo-open", learner, 5, "Review text")
    assert failure.value.status_code == 404 and database.reviews.count_documents({}) == 0


def test_reviews_are_scoped_and_historical_paid_access_is_valid(learner_http, database):
    enrollment(database)
    paid = enrollment(database, "payment", "paid", "invited")
    assert learner_http.post("/courses/demo-open/reviews", json={"rating": 5, "comment": "Open course"}).status_code == 200
    assert learner_http.post("/courses/demo-payment/reviews", json={"rating": 2, "comment": "Paid course"}).status_code == 200
    assert learner_http.get("/courses/demo-open/reviews").json()["learnerDraft"] == "Open course"
    assert learner_http.get("/courses/demo-payment/reviews").json()["learnerDraft"] == "Paid course"
    assert database.enrollments.find_one({"_id": paid["_id"]}) == paid and database.payment_orders.count_documents({}) == 0


def test_review_average_rounding_and_exact_comment(courses, database, learner):
    users = list(database.users.find().sort("_id", 1))
    for user, rating in zip(users, (1, 4, 5)):
        enrollment(database, user=user["_id"])
        result = courses.submit_course_review("demo-open", {"id": user["_id"], "name": user["name"]}, rating, "   ")
    assert result["averageRating"] == 3.3 and result["totalReviews"] == 3
    assert result["learnerDraft"] == "   "  # Existing Pydantic length contract does not trim comments.


def test_concurrent_review_upsert_is_unique(courses, database, learner, monkeypatch):
    enrollment(database)
    synchronize(monkeypatch, courses, courses)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda rating: courses.submit_course_review("demo-open", learner, rating, f"Rating {rating}"), (3, 5)))
    assert all(row["totalReviews"] == 1 for row in results)
    assert database.reviews.count_documents({}) == 1
    assert database.reviews.find_one()["rating"] in (3, 5)


def test_concurrent_reviews_different_users_have_correct_average(courses, database, learner, monkeypatch):
    enrollment(database)
    instructor = database.users.find_one({"_id": fixture_id("instructor")})
    other = {"id": instructor["_id"], "name": instructor["name"]}
    enrollment(database, user=other["id"])
    synchronize(monkeypatch, courses, courses)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(courses.submit_course_review, "demo-open", learner, 4, "First review")
        second = pool.submit(courses.submit_course_review, "demo-open", other, 5, "Second review")
        first.result(); second.result()
    result = courses.get_course_reviews_for_user("demo-open", learner)
    assert result["totalReviews"] == 2 and result["averageRating"] == 4.5


def test_review_failure_after_write_rolls_back_all_collections(courses, database, learner, monkeypatch):
    enrollment(database)
    before = snapshot(database)
    def fail(*args): raise HTTPException(409, "Injected review response failure")
    monkeypatch.setattr(courses, "_reviews", fail)
    with pytest.raises(HTTPException): courses.submit_course_review("demo-open", learner, 5, "Review text")
    assert snapshot(database) == before


def test_review_validator_failure_is_atomic(courses, database, learner, monkeypatch):
    from pymongo.synchronous.collection import Collection
    enrollment(database)
    before = snapshot(database)
    original = Collection.update_one
    def invalid(self, query, update, *args, **kwargs):
        if self.name == "reviews": update["$set"]["rating"] = 0
        return original(self, query, update, *args, **kwargs)
    monkeypatch.setattr(Collection, "update_one", invalid)
    with pytest.raises(HTTPException) as failure: courses.submit_course_review("demo-open", learner, 5, "Review text")
    assert failure.value.status_code == 422 and snapshot(database) == before


def test_review_transient_retry_preserves_identity(courses, database, learner, monkeypatch):
    enrollment(database)
    original, identifiers = courses._reviews, []
    def retry(course, user, enrolled, session=None):
        result = original(course, user, enrolled, session)
        identifiers.append(database.reviews.find_one(session=session)["_id"])
        if len(identifiers) == 1:
            raise OperationFailure("Injected transient failure", 112, {"errorLabels": ["TransientTransactionError"]})
        return result
    monkeypatch.setattr(courses, "_reviews", retry)
    assert courses.submit_course_review("demo-open", learner, 5, "Review text")["totalReviews"] == 1
    assert len(identifiers) == 2 and identifiers[0] == identifiers[1]
    assert database.reviews.count_documents({}) == 1


def test_concurrent_review_and_course_delete_leave_no_orphan(courses, database, learner, monkeypatch):
    enrollment(database)
    admin = MongoAdminService(database)
    synchronize(monkeypatch, courses, admin)
    def review():
        try:
            courses.submit_course_review("demo-open", learner, 5, "Review text")
            return 200
        except HTTPException as failure: return failure.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        write = pool.submit(review)
        deletion = pool.submit(admin.delete_admin_course, "demo-open")
        assert deletion.result()["deleted"] and write.result() in (200, 404)
    assert database.reviews.count_documents({}) == 0


def test_review_writes_never_open_postgres(learner_http, database, monkeypatch):
    enrollment(database)
    def fail(): raise AssertionError("MongoDB review writes must not open PostgreSQL")
    for module in ("courses", "admin", "auth"):
        monkeypatch.setattr(f"backend.modules.{module}.service.connect", fail)
    assert learner_http.post("/courses/demo-open/reviews", json={"rating": 5, "comment": "Review text"}).status_code == 200


@pytest.mark.parametrize("mode", ["video", "document", "image"])
@pytest.mark.parametrize("status", ["not_started", "in_progress", "completed"])
def test_progress_modes_status_position_and_summary(learner_http, database, mode, status):
    enrollment(database)
    path = f"/courses/demo-open/content/demo-{mode}/progress"
    response = learner_http.post(path, json={"status": status, "lastPosition": 42})
    assert response.status_code == 200
    body = response.json()
    assert body["courseId"] == "demo-open" and body["contentItem"]["status"] == status
    assert "isLocked" not in body["contentItem"]
    expected_count = 1 if status == "completed" else 0
    assert body["progress"] == {"totalCount": 4, "completedCount": expected_count,
        "incompleteCount": 4 - expected_count, "completionPercentage": 25.0 * expected_count,
        "status": "yet_to_start" if status == "not_started" else "in_progress"}
    row = database.content_progress.find_one()
    assert row["last_position"] == 42 and row["course_id"] == fixture_id("course-open")
    assert (row["completed_at"] is not None) == (status == "completed")
    assert learner_http.post(path, json={"status": status, "lastPosition": 0}).status_code == 200
    assert database.content_progress.find_one()["_id"] == row["_id"]
    assert database.content_progress.find_one()["last_position"] == 0
    assert database.content_progress.count_documents({}) == database.course_progress.count_documents({}) == 1
    assert database.quiz_attempts.count_documents({}) == database.point_events.count_documents({}) == database.learner_points.count_documents({}) == 0


def test_completion_timestamp_lifecycle_preserves_legacy_updates(learner_http, database, monkeypatch):
    enrollment(database)
    MongoAdminService(database).delete_quiz_detail(fixture_id("quiz"))
    complete_lesson(database, "document")
    complete_lesson(database, "image")
    stamp = datetime(2026, 3, 1, tzinfo=timezone.utc)
    monkeypatch.setattr("backend.modules.courses.mongo_service.now", lambda: stamp)
    path = "/courses/demo-open/content/demo-video/progress"
    first = learner_http.post(path, json={"status": "completed", "lastPosition": 100})
    assert first.json()["progress"]["status"] == "completed"
    initial_summary = database.course_progress.find_one()
    assert initial_summary["started_at"] == initial_summary["completed_at"] == stamp
    stamp += timedelta(days=1)
    assert learner_http.post(path, json={"status": "completed", "lastPosition": 100}).status_code == 200
    assert database.content_progress.find_one({"content_id": fixture_id("content-video")})["completed_at"] == stamp
    assert database.course_progress.find_one()["completed_at"] == stamp
    assert database.course_progress.find_one()["started_at"] == initial_summary["started_at"]
    stamp += timedelta(days=1)
    reopened = learner_http.post(path, json={"status": "in_progress", "lastPosition": 0}).json()
    assert reopened["progress"]["status"] == "in_progress" and reopened["progress"]["completionPercentage"] == 66.67
    assert database.course_progress.find_one()["completed_at"] is None
    assert database.content_progress.find_one({"content_id": fixture_id("content-video")})["completed_at"] is None
    stamp += timedelta(days=1)
    assert learner_http.post(path, json={"status": "completed", "lastPosition": 100}).json()["progress"]["completionPercentage"] == 100.0
    assert database.course_progress.find_one()["completed_at"] == stamp
    assert database.course_progress.find_one()["_id"] == initial_summary["_id"]


@pytest.mark.parametrize("payment,expected", [(None, 403), ("pending", 403), ("paid", 200), ("not_required", 200)])
def test_progress_enrollment_access(learner_http, database, payment, expected):
    if payment: enrollment(database, payment=payment)
    before = snapshot(database)
    response = learner_http.post("/courses/demo-open/content/demo-video/progress", json={"status": "completed", "lastPosition": 10})
    assert response.status_code == expected
    if expected != 200: assert snapshot(database) == before


@pytest.mark.parametrize("slug", ["missing", "demo-open"])
def test_progress_missing_or_unpublished_course(learner_http, database, slug):
    enrollment(database)
    database.courses.update_one({"slug": "demo-open"}, {"$set": {"is_published": False}})
    before = snapshot(database)
    assert learner_http.post(f"/courses/{slug}/content/demo-video/progress", json={"status": "completed"}).status_code == 404
    assert snapshot(database) == before


@pytest.mark.parametrize("status,position", [("invalid", 0), ("completed", -1), ("completed", 1.5), ("completed", 2 ** 80)])
def test_invalid_progress_does_not_mutate(learner_http, database, status, position):
    enrollment(database)
    before = snapshot(database)
    assert learner_http.post("/courses/demo-open/content/demo-video/progress", json={"status": status, "lastPosition": position}).status_code == 422
    assert snapshot(database) == before


def test_progress_auth_missing_user_and_missing_content(learner_http, database, courses, learner):
    learner_http.headers.clear()
    assert learner_http.post("/courses/demo-open/content/demo-video/progress", json={"status": "completed"}).status_code == 401
    learner["id"] = str(uuid4())
    with pytest.raises(HTTPException) as failure:
        courses.update_content_progress_for_user("demo-open", "demo-video", learner, status_value="completed", last_position=0)
    assert failure.value.status_code == 404
    enrollment(database)
    learner_http.headers.update(bearer(fixture_id("learner"), role="learner", email="learner@learnova.example"))
    assert learner_http.post("/courses/demo-open/content/missing/progress", json={"status": "completed"}).status_code == 404


@pytest.mark.parametrize("status", ["not_started", "in_progress", "completed"])
def test_quiz_progress_cannot_bypass_submission(learner_http, database, status):
    enrollment(database)
    path = "/courses/demo-open/content/demo-quiz/progress"
    assert learner_http.post(path, json={"status": status}).status_code == 403
    for mode in ("video", "document", "image"): complete_lesson(database, mode)
    before = snapshot(database)
    assert learner_http.post(path, json={"status": status}).status_code == 400
    assert snapshot(database) == before


def test_progress_scope_and_other_user_work(learner_http, database):
    enrollment(database)
    enrollment(database, "payment", "paid")
    other = MongoAdminService(database).create_course_content("demo-payment", lesson_payload())
    for mode in ("video", "document", "image"): complete_lesson(database, mode, user=fixture_id("instructor"))
    assert learner_http.post("/courses/demo-payment/content/demo-video/progress", json={"status": "completed"}).status_code == 404
    result = learner_http.post("/courses/demo-open/content/demo-video/progress", json={"status": "completed"}).json()
    assert result["progress"]["completedCount"] == 1 and result["progress"]["completionPercentage"] == 25.0
    assert learner_http.post(f"/courses/demo-payment/content/{other['slug']}/progress", json={"status": "completed"}).json()["progress"]["completionPercentage"] == 100.0
    assert database.payment_orders.count_documents({}) == 0


def test_progress_rejects_existing_wrong_course_reference(learner_http, database):
    enrollment(database)
    complete_lesson(database, "video")
    database.content_progress.update_one({}, {"$set": {"course_id": fixture_id("course-payment")}})
    before = snapshot(database)
    assert learner_http.post("/courses/demo-open/content/demo-video/progress", json={"status": "completed"}).status_code == 409
    assert snapshot(database) == before


def test_progress_rounding_and_orphan_exclusion(learner_http, database):
    enrollment(database)
    MongoAdminService(database).delete_quiz_detail(fixture_id("quiz"))
    database.content_progress.insert_one({"_id": str(uuid4()), "schema_version": 1, "course_id": fixture_id("course-open"),
        "content_id": str(uuid4()), "user_id": fixture_id("learner"), "status": "completed", "last_position": 0,
        "updated_at": datetime.now(timezone.utc)})
    for mode, percentage in (("video", 33.33), ("document", 66.67), ("image", 100.0)):
        response = learner_http.post(f"/courses/demo-open/content/demo-{mode}/progress", json={"status": "completed"})
        assert response.status_code == 200 and response.json()["progress"]["completionPercentage"] == percentage
    assert database.course_progress.find_one()["completed_count"] == 3
    assert database.content_progress.count_documents({}) == 4  # No silent orphan/source cleanup.


@pytest.mark.parametrize("stage", ["before_summary", "after_summary"])
def test_progress_failure_rolls_back_content_summary_and_parent(courses, database, learner, monkeypatch, stage):
    enrollment(database)
    before = snapshot(database)
    def fail(*args, **kwargs): raise HTTPException(409, "Injected progress write-stage failure")
    monkeypatch.setattr(courses, "_recalculate_course_progress" if stage == "before_summary" else "_content_items", fail)
    with pytest.raises(HTTPException):
        courses.update_content_progress_for_user("demo-open", "demo-video", learner, status_value="completed", last_position=10)
    assert snapshot(database) == before


def test_summary_validator_failure_rolls_back_lesson(courses, database, learner, monkeypatch):
    from pymongo.synchronous.collection import Collection
    enrollment(database)
    before, original = snapshot(database), Collection.update_one
    def invalid(self, query, update, *args, **kwargs):
        if self.name == "course_progress": update["$set"]["completion_percentage"] = 101.0
        return original(self, query, update, *args, **kwargs)
    monkeypatch.setattr(Collection, "update_one", invalid)
    with pytest.raises(HTTPException) as failure:
        courses.update_content_progress_for_user("demo-open", "demo-video", learner, status_value="completed", last_position=10)
    assert failure.value.status_code == 422 and snapshot(database) == before


def test_progress_transient_retry_reuses_content_and_summary_ids(courses, database, learner, monkeypatch):
    enrollment(database)
    original, identities = courses._content_items, []
    def retry(course_id, user_id, session=None):
        result = original(course_id, user_id, session)
        identities.append((database.content_progress.find_one(session=session)["_id"], database.course_progress.find_one(session=session)["_id"]))
        if len(identities) == 1:
            raise OperationFailure("Injected transient failure", 112, {"errorLabels": ["TransientTransactionError"]})
        return result
    monkeypatch.setattr(courses, "_content_items", retry)
    assert courses.update_content_progress_for_user("demo-open", "demo-video", learner, status_value="completed", last_position=10)["progress"]["completedCount"] == 1
    assert len(identities) == 2 and identities[0] == identities[1]
    assert database.content_progress.count_documents({}) == database.course_progress.count_documents({}) == 1


def test_concurrent_different_lessons_keep_summary_consistent(courses, database, learner, monkeypatch):
    enrollment(database)
    synchronize(monkeypatch, courses, courses)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda mode: courses.update_content_progress_for_user(
            "demo-open", "demo-" + mode, learner, status_value="completed", last_position=100), ("video", "document")))
    assert sorted(row["progress"]["completedCount"] for row in results) == [1, 2]
    summary = database.course_progress.find_one()
    assert summary["completed_count"] == 2 and summary["incomplete_count"] == 2 and summary["completion_percentage"] == 50.0
    assert database.content_progress.count_documents({}) == 2


def test_concurrent_duplicate_completion_does_not_double_count(courses, database, learner, monkeypatch):
    enrollment(database)
    synchronize(monkeypatch, courses, courses)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: courses.update_content_progress_for_user(
            "demo-open", "demo-video", learner, status_value="completed", last_position=100), (1, 2)))
    assert all(row["progress"]["completedCount"] == 1 for row in results)
    assert database.content_progress.count_documents({}) == 1


@pytest.mark.parametrize("target", ["course", "content"])
def test_concurrent_delete_and_progress_do_not_orphan(courses, database, learner, monkeypatch, target):
    enrollment(database)
    admin = MongoAdminService(database)
    synchronize(monkeypatch, courses, admin)
    def write():
        try:
            courses.update_content_progress_for_user("demo-open", "demo-video", learner, status_value="completed", last_position=10)
            return 200
        except HTTPException as failure: return failure.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        progress = pool.submit(write)
        deletion = pool.submit(admin.delete_admin_course, "demo-open") if target == "course" else pool.submit(
            admin.delete_course_content, "demo-video", "demo-open")
        assert deletion.result()["deleted"] and progress.result() in (200, 404)
    assert database.content_progress.count_documents({"content_id": fixture_id("content-video")}) == 0
    summary = database.course_progress.find_one()
    if target == "course": assert summary is None
    elif summary: assert summary["current_content_id"] is None


def test_content_add_remove_preserves_history_until_normal_update(learner_http, database):
    enrollment(database)
    admin = MongoAdminService(database)
    admin.delete_quiz_detail(fixture_id("quiz"))
    for mode in ("video", "document", "image"):
        assert learner_http.post(f"/courses/demo-open/content/demo-{mode}/progress", json={"status": "completed"}).status_code == 200
    previous = database.course_progress.find_one()
    added = admin.create_course_content("demo-open", lesson_payload())
    assert database.course_progress.find_one() == previous
    assert learner_http.post("/courses/demo-open/content/demo-video/progress", json={"status": "completed"}).json()["progress"]["completionPercentage"] == 75.0
    previous = database.course_progress.find_one()
    admin.delete_course_content(added["slug"], "demo-open")
    assert database.course_progress.find_one() == previous
    assert learner_http.post("/courses/demo-open/content/demo-video/progress", json={"status": "completed"}).json()["progress"]["completionPercentage"] == 100.0


def test_empty_course_recalculation_keeps_sql_zero_percent_completed(courses, database, learner):
    stamp = datetime(2026, 3, 1, tzinfo=timezone.utc)
    def recalculate(session):
        course = lock_course(database, fixture_id("course-payment"), session)
        return courses._recalculate_course_progress(course["_id"], learner["id"], None, session, stamp=stamp, identifier=str(uuid4()))
    result = courses._transaction(recalculate)
    assert result == {"totalCount": 0, "completedCount": 0, "incompleteCount": 0, "completionPercentage": 0.0, "status": "completed"}
    assert database.course_progress.find_one()["completed_at"] == stamp


def test_existing_null_start_time_remains_preserved(learner_http, database):
    enrollment(database)
    row = {"_id": str(uuid4()), "schema_version": 1, "course_id": fixture_id("course-open"), "user_id": fixture_id("learner"),
        "completed_count": 3, "incomplete_count": 99, "completion_percentage": 17.0, "status": "in_progress", "started_at": None,
        "updated_at": datetime.now(timezone.utc)}
    database.course_progress.insert_one(row)
    result = learner_http.post("/courses/demo-open/content/demo-video/progress", json={"status": "completed"}).json()
    assert result["progress"]["completionPercentage"] == 25.0 and result["progress"]["incompleteCount"] == 3
    assert database.course_progress.find_one()["started_at"] is None
    assert database.course_progress.find_one()["_id"] == row["_id"]


def test_progress_writes_never_open_postgres(learner_http, database, monkeypatch):
    enrollment(database)
    def fail(): raise AssertionError("MongoDB progress writes must not open PostgreSQL")
    for module in ("courses", "admin", "auth"):
        monkeypatch.setattr(f"backend.modules.{module}.service.connect", fail)
    assert learner_http.post("/courses/demo-open/content/demo-image/progress", json={"status": "completed", "lastPosition": 0}).status_code == 200
