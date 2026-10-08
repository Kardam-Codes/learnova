"""Real MongoDB learner API, access, batching, and enrollment transaction checks."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pymongo import MongoClient, monitoring
from pymongo.errors import OperationFailure
import pytest

from backend.config.mongo import get_mongo_settings
from backend.db.mongo.seed import fixture_id
from backend.main import app
from backend.modules.admin.mongo_service import MongoAdminService
from backend.modules.courses.mongo_service import MongoCourseService
from backend.tests.test_mongo_admin import course_payload, lesson_payload
from backend.tests.test_mongo_auth import bearer


@pytest.fixture
def learner(database):
    user = database.users.find_one({"_id": fixture_id("learner")})
    return {"id": user["_id"], "name": user["name"], "role": user["role"], "email": user["email"]}


@pytest.fixture
def courses(database):
    return MongoCourseService(database)


@pytest.fixture
def learner_http(database, monkeypatch):
    monkeypatch.setenv("AUTH_STORAGE", "mongo")
    monkeypatch.setenv("ADMIN_STORAGE", "mongo")
    monkeypatch.setenv("COURSES_STORAGE", "mongo")
    monkeypatch.setenv("MONGODB_DB", database.name)
    with TestClient(app) as client:
        client.headers.update(bearer(fixture_id("learner"), role="learner", email="learner@learnova.example"))
        yield client


def enrollment(database, access="open", payment="not_required", source="self", user=None):
    row = {"_id": str(uuid4()), "schema_version": 1, "course_id": fixture_id("course-" + access),
        "user_id": user or fixture_id("learner"), "enrolled_at": datetime.now(timezone.utc),
        "enrollment_source": source, "payment_status": payment}
    database.enrollments.insert_one(row)
    return database.enrollments.find_one({"_id": row["_id"]})


def complete_lesson(database, mode, *, user=None, status="completed"):
    row = {"_id": str(uuid4()), "schema_version": 1, "course_id": fixture_id("course-open"),
        "user_id": user or fixture_id("learner"), "content_id": fixture_id("content-" + mode),
        "status": status, "last_position": 0, "updated_at": datetime.now(timezone.utc)}
    database.content_progress.insert_one(row)


def test_catalog_profile_and_enrollment_http(learner_http, database):
    before = learner_http.get("/courses")
    assert before.status_code == 200
    payload = before.json()
    assert payload["courses"] == payload["enrolledCourses"] == []
    assert len(payload["availableCourses"]) == 2
    assert payload["profile"]["currentBadge"] == "Newbie" and payload["profile"]["totalPoints"] == 0
    assert len(payload["profile"]["badgeTiers"]) == 6
    paid = next(item for item in payload["availableCourses"] if item["id"] == "demo-payment")
    assert paid["price"] == 99.0 and paid["paymentStatus"] == "pending" and paid["isPurchased"] is False
    detail = learner_http.get("/courses/demo-open").json()
    assert detail["canEnrollFree"] and not detail["isEnrolled"]
    assert all(item["isLocked"] for item in detail["contentItems"])
    enrolled = learner_http.post("/courses/demo-open/enroll")
    assert enrolled.status_code == 200 and enrolled.json()["isEnrolled"]
    after = learner_http.get("/courses").json()
    assert after["courses"] == after["enrolledCourses"] and len(after["courses"]) == 1
    assert after["courses"][0]["firstContentId"] == "demo-video"
    assert database.course_progress.count_documents({}) == 0  # Enrollment does not manufacture progress.


def test_profile_uses_preserved_points_and_stored_name(learner_http, database):
    database.learner_points.insert_one({"_id": str(uuid4()), "schema_version": 1, "user_id": fixture_id("learner"),
        "total_points": 35, "current_badge": "Explorer", "updated_at": datetime.now(timezone.utc)})
    database.users.update_one({"_id": fixture_id("learner")}, {"$set": {"name": "Updated learner"}})
    profile = learner_http.get("/courses").json()["profile"]
    assert profile["learnerName"] == "Updated learner" and profile["totalPoints"] == 35 and profile["currentBadge"] == "Explorer"


@pytest.mark.parametrize("visibility", ["everyone", "signed_in"])
def test_publication_and_authenticated_visibility(learner_http, database, visibility):
    database.courses.update_one({"slug": "demo-open"}, {"$set": {"visibility": visibility, "is_published": False}})
    assert len(learner_http.get("/courses").json()["availableCourses"]) == 1
    for method, path in [("GET", "/courses/demo-open"), ("POST", "/courses/demo-open/enroll"),
                         ("GET", "/courses/demo-open/content/demo-video"), ("GET", "/courses/demo-open/quizzes/demo-quiz")]:
        assert learner_http.request(method, path).status_code == 404
    database.courses.update_one({"slug": "demo-open"}, {"$set": {"is_published": True}})
    assert learner_http.get("/courses/demo-open").status_code == 200
    learner_http.headers.clear()
    assert learner_http.get("/courses").status_code == 401


@pytest.mark.parametrize("access,payment,enrolled,status", [
    ("open", "not_required", True, 200), ("open", "paid", True, 200), ("open", "pending", False, 403),
    ("payment", "paid", True, 200), ("payment", "pending", False, 403), ("payment", "not_required", True, 200),
])
def test_existing_enrollment_access_matrix(learner_http, database, access, payment, enrolled, status):
    if access == "payment":
        MongoAdminService(database).create_course_content("demo-payment", lesson_payload())
    enrollment(database, access, payment)
    detail = learner_http.get("/courses/demo-" + access).json()
    assert detail["isEnrolled"] is enrolled
    slug = "demo-video" if access == "open" else "new-lesson"
    assert learner_http.get(f"/courses/demo-{access}/content/{slug}").status_code == status
    assert database.payment_orders.count_documents({}) == 0  # Historical paid access does not require an order.


def test_invitation_access_and_existing_membership_preserved(learner_http, database):
    database.courses.update_one({"slug": "demo-open"}, {"$set": {"access_rule": "invitation"}})
    assert learner_http.post("/courses/demo-open/enroll").status_code == 403
    assert learner_http.get("/courses/demo-open/content/demo-video").status_code == 403
    before = enrollment(database, source="invited")
    response = learner_http.post("/courses/demo-open/enroll")
    assert response.status_code == 200 and response.json()["isEnrolled"]
    assert database.enrollments.find_one() == before


def test_paid_course_self_enrollment_requires_payment_and_retains_paid_access(learner_http, database):
    assert learner_http.post("/courses/demo-payment/enroll").status_code == 400
    assert database.enrollments.count_documents({}) == 0
    before = enrollment(database, "payment", "paid", "admin_added")
    assert learner_http.post("/courses/demo-payment/enroll").json()["isEnrolled"]
    assert database.enrollments.find_one() == before


def test_repeated_open_enrollment_upgrades_pending_without_resetting_identity(learner_http, database):
    before = enrollment(database, payment="pending", source="invited")
    for _ in range(2):
        assert learner_http.post("/courses/demo-open/enroll").status_code == 200
    after = database.enrollments.find_one()
    assert after["_id"] == before["_id"] and after["enrolled_at"] == before["enrolled_at"]
    assert after["payment_status"] == "not_required" and after["enrollment_source"] == "self"
    assert database.enrollments.count_documents({}) == 1


def test_confirmed_lesson_access_and_quiz_lock_rules(learner_http, database):
    enrollment(database)
    # Later lessons stay available without completing the first lesson, as user confirmed.
    for mode in ("video", "document", "image"):
        response = learner_http.get("/courses/demo-open/content/demo-" + mode)
        assert response.status_code == 200 and response.json()["contentItem"]["mode"] == mode
        assert "isLocked" not in response.json()["contentItem"]
    assert learner_http.get("/courses/demo-open/quizzes/demo-video").status_code == 400
    assert learner_http.get("/courses/demo-open/quizzes/demo-quiz").status_code == 403
    for mode in ("video", "document"):
        complete_lesson(database, mode)
    complete_lesson(database, "image", user=fixture_id("instructor"))
    assert learner_http.get("/courses/demo-open/quizzes/demo-quiz").status_code == 403
    complete_lesson(database, "image")
    response = learner_http.get("/courses/demo-open/quizzes/demo-quiz")
    assert response.status_code == 200
    assert response.json()["contentItem"]["nextContentId"] is None


def test_first_quiz_without_prior_lessons_is_accessible(learner_http, database):
    enrollment(database)
    database.course_content.update_many({"content_mode": {"$ne": "quiz"}}, {"$inc": {"display_order": 10}})
    assert learner_http.get("/courses/demo-open/quizzes/demo-quiz").status_code == 200


def test_content_modes_attachments_order_and_next_routing(learner_http, database):
    enrollment(database)
    admin = MongoAdminService(database)
    created = admin.create_course_content("demo-open", lesson_payload(attachments=[
        {"label": "External", "url": "https://example.com", "attachmentType": "link"},
        {"label": "Download", "url": "/uploads/notes.pdf", "attachmentType": "file"}]))
    items = learner_http.get("/courses/demo-open").json()["contentItems"]
    assert [item["order"] for item in items] == [1, 2, 3, 4, 5]
    assert [item["nextContentId"] for item in items] == ["demo-document", "demo-image", "demo-quiz", "new-lesson", None]
    direct = learner_http.get("/courses/demo-open/content/new-lesson").json()["contentItem"]
    assert [item["id"] for item in direct["attachments"]] == [item["id"] for item in created["attachments"]]
    assert [item["label"] for item in direct["attachments"]] == ["External", "Download"]
    assert all("attachmentType" not in item for item in direct["attachments"])  # Existing learner contract.


def test_course_scoped_content_and_progress_never_leak(learner_http, database):
    admin = MongoAdminService(database)
    one = admin.create_course_content("demo-open", lesson_payload())
    two = admin.create_course_content("demo-payment", lesson_payload(description="Other course"))
    assert one["slug"] == two["slug"]
    enrollment(database)
    enrollment(database, "payment", "paid")
    first = learner_http.get("/courses/demo-open/content/new-lesson").json()["contentItem"]
    second = learner_http.get("/courses/demo-payment/content/new-lesson").json()["contentItem"]
    assert first["description"] != second["description"]
    assert learner_http.get("/courses/demo-payment/content/demo-video").status_code == 404
    assert learner_http.get("/courses/demo-open/content/missing").status_code == 404


def test_learner_quiz_serialization_omits_correct_answers(learner_http, database):
    quiz = database.quizzes.find_one()
    quiz["questions"][0]["options"][1]["is_correct"] = True
    database.quizzes.replace_one({"_id": quiz["_id"]}, quiz)
    payload = learner_http.get("/courses/demo-open").json()
    question = payload["contentItems"][-1]["quizQuestions"][0]
    assert question["allowsMultipleAnswers"] and question["options"] == ["Yes", "No"]
    def check(value):
        if isinstance(value, dict):
            assert not ({"isCorrect", "is_correct", "_correctOptionIndexes", "password_hash"} & set(value))
            for item in value.values(): check(item)
        elif isinstance(value, list):
            for item in value: check(item)
    check(payload)


def test_empty_quizzes_and_questions_without_options_follow_legacy_reads(learner_http, database):
    database.quizzes.update_one({}, {"$set": {"questions": []}})
    item = learner_http.get("/courses/demo-open").json()["contentItems"][-1]
    assert item["mode"] == "quiz" and "quizQuestions" not in item and "quizRules" not in item
    quiz = database.quizzes.find_one()
    quiz["questions"] = [{"id": str(uuid4()), "question_text": "Unfinished draft", "display_order": 1,
        "options": [], "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)}]
    database.quizzes.replace_one({"_id": quiz["_id"]}, quiz)
    assert "quizQuestions" not in learner_http.get("/courses/demo-open").json()["contentItems"][-1]


def test_resume_selection_and_stored_progress_summary_preserved(learner_http, database):
    enrollment(database)
    complete_lesson(database, "video")
    complete_lesson(database, "document", status="in_progress")
    card = learner_http.get("/courses").json()["courses"][0]
    assert card["lastContentId"] == "demo-document" and card["lastContentMode"] == "document"
    database.course_progress.insert_one({"_id": str(uuid4()), "schema_version": 1,
        "course_id": fixture_id("course-open"), "user_id": fixture_id("learner"), "completion_percentage": 12.5,
        "completed_count": 2, "incomplete_count": 7, "status": "in_progress",
        "current_content_id": fixture_id("content-image"), "updated_at": datetime.now(timezone.utc)})
    before = database.course_progress.find_one()
    card = learner_http.get("/courses").json()["courses"][0]
    assert card["lastContentId"] == "demo-image" and card["lastContentMode"] == "document"  # Existing SQL choice.
    assert card["hasStarted"] and card["isInProgress"]
    progress = learner_http.get("/courses/demo-open").json()["progress"]
    assert progress == {"completionPercentage": 12.5, "completedCount": 2, "incompleteCount": 7, "totalCount": 4}
    assert database.course_progress.find_one() == before


def test_resume_pointer_must_belong_to_requested_course(learner_http, database):
    foreign = MongoAdminService(database).create_course_content("demo-payment", lesson_payload())
    enrollment(database)
    database.course_progress.insert_one({"_id": str(uuid4()), "schema_version": 1, "course_id": fixture_id("course-open"),
        "user_id": fixture_id("learner"), "completion_percentage": 0.0, "completed_count": 0, "incomplete_count": 4,
        "status": "yet_to_start", "current_content_id": foreign["id"], "updated_at": datetime.now(timezone.utc)})
    assert learner_http.get("/courses").json()["courses"][0]["lastContentId"] == "demo-video"


def test_reviews_and_responsible_name_are_mongo_reads(learner_http, database):
    database.courses.update_one({"slug": "demo-open"}, {"$set": {"responsible_user_id": fixture_id("instructor")}})
    stamp = datetime.now(timezone.utc)
    for index, (user, rating) in enumerate((("learner", 4), ("instructor", 5))):
        database.reviews.insert_one({"_id": str(uuid4()), "schema_version": 1, "course_id": fixture_id("course-open"),
            "user_id": fixture_id(user), "rating": rating, "comment": "Review " + str(index),
            "created_at": stamp + timedelta(seconds=index), "updated_at": stamp})
    detail = learner_http.get("/courses/demo-open").json()
    assert detail["providerName"] == "Demo instructor"
    reviews = learner_http.get("/courses/demo-open/reviews").json()
    assert reviews == detail["reviews"]
    assert reviews["averageRating"] == 4.5 and reviews["totalReviews"] == 2 and reviews["learnerDraft"] == "Review 0"
    assert reviews["items"][0]["authorName"] == "Demo learner"
    assert learner_http.get("/courses/missing/reviews").json()["items"] == []
    database.courses.update_one({"slug": "demo-open"}, {"$set": {"is_published": False}})
    assert learner_http.get("/courses/demo-open/reviews").json()["totalReviews"] == 2
    assert learner_http.get("/courses/demo-open/reviews").json()["isEnrolled"] is False


def test_equal_review_timestamp_order_is_stable(learner_http, database):
    stamp = datetime.now(timezone.utc)
    identifiers = sorted((str(uuid4()), str(uuid4())))
    for identifier, user in zip(reversed(identifiers), ("learner", "instructor")):
        database.reviews.insert_one({"_id": identifier, "schema_version": 1, "course_id": fixture_id("course-open"),
            "user_id": fixture_id(user), "rating": 5, "comment": "Same timestamp", "created_at": stamp, "updated_at": stamp})
    for _ in range(2):
        assert [item["id"] for item in learner_http.get("/courses/demo-open/reviews").json()["items"]] == identifiers


@pytest.mark.parametrize("same_timestamp,change_field,accepted", [(True, False, True), (False, False, False), (True, True, False)])
def test_source_comparison_only_normalizes_proven_review_ties(same_timestamp, change_field, accepted):
    from backend.db.migration.verify_phase5_baseline import compare_learner_checks
    stamp = datetime.now(timezone.utc)
    source = {"course_reviews": [{"id": "a", "course_id": "course", "created_at": stamp},
        {"id": "b", "course_id": "course", "created_at": stamp if same_timestamp else stamp + timedelta(seconds=1)}]}
    original = [{"method": "GET", "path": "/courses/example/reviews", "status": 200, "role": "learner",
        "response": {"items": [{"id": "a", "comment": "First"}, {"id": "b", "comment": "Second"}]}}]
    changed = deepcopy(original)
    changed[0]["response"]["items"].reverse()
    if change_field: changed[0]["response"]["items"][0]["comment"] = "Changed"
    if accepted:
        assert compare_learner_checks(original, changed, source)["responses_preserved"] == 1
    else:
        with pytest.raises(RuntimeError): compare_learner_checks(original, changed, source)


def test_empty_course_catalog_and_enrollment(learner_http, database):
    detail = learner_http.get("/courses/demo-payment").json()
    assert detail["contentItems"] == [] and detail["progress"]["totalCount"] == 0
    admin = MongoAdminService(database)
    created = admin.create_admin_course({"id": fixture_id("instructor")}, course_payload(isPublished=True))
    enrolled = learner_http.post(f"/courses/{created['slug']}/enroll").json()
    assert enrolled["isEnrolled"] and enrolled["contentItems"] == []
    card = learner_http.get("/courses").json()["courses"][0]
    assert card["firstContentId"] is None and card["lastContentId"] is None and card["lastContentMode"] is None


def test_concurrent_enrollment_is_unique(courses, database, learner, monkeypatch):
    barrier, original = Barrier(2), courses._transaction
    def synchronized(callback):
        barrier.wait(timeout=10)
        return original(callback)
    monkeypatch.setattr(courses, "_transaction", synchronized)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: courses.enroll_in_course("demo-open", learner), (1, 2)))
    assert all(item["isEnrolled"] for item in results)
    assert database.enrollments.count_documents({}) == 1


def test_concurrent_admin_invitation_never_downgrades_paid(courses, database, learner, monkeypatch):
    admin, barrier = MongoAdminService(database), Barrier(2)
    for service in (courses, admin):
        original = service._transaction
        def synchronized(callback, run=original):
            barrier.wait(timeout=10)
            return run(callback)
        monkeypatch.setattr(service, "_transaction", synchronized)
    with ThreadPoolExecutor(max_workers=2) as pool:
        free = pool.submit(courses.enroll_in_course, "demo-open", learner)
        paid = pool.submit(admin.add_course_attendees, "demo-open", [{"email": learner["email"], "name": learner["name"],
            "enrollmentSource": "admin_added", "paymentStatus": "paid"}])
        assert free.result()["isEnrolled"]
        assert paid.result()["attendees"][0]["paymentStatus"] == "paid"
    assert database.enrollments.count_documents({}) == 1 and database.enrollments.find_one()["payment_status"] == "paid"


def test_concurrent_enrollment_and_course_delete_leave_no_orphan(courses, database, learner, monkeypatch):
    admin, barrier = MongoAdminService(database), Barrier(2)
    for service in (courses, admin):
        original = service._transaction
        def synchronized(callback, run=original):
            barrier.wait(timeout=10)
            return run(callback)
        monkeypatch.setattr(service, "_transaction", synchronized)
    def enroll():
        try:
            courses.enroll_in_course("demo-open", learner)
            return 200
        except HTTPException as failure:
            return failure.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(enroll)
        second = pool.submit(admin.delete_admin_course, "demo-open")
        assert second.result()["deleted"] and first.result() in (200, 404)
    assert database.enrollments.count_documents({}) == 0 and database.courses.find_one({"slug": "demo-open"}) is None


def test_enrollment_response_failure_rolls_back_parent_and_enrollment(courses, database, learner, monkeypatch):
    before = database.courses.find_one({"slug": "demo-open"})
    def fail(*args): raise HTTPException(409, "Injected failure after enrollment write")
    monkeypatch.setattr(courses, "_detail", fail)
    with pytest.raises(HTTPException):
        courses.enroll_in_course("demo-open", learner)
    assert database.enrollments.count_documents({}) == 0
    assert database.courses.find_one({"slug": "demo-open"}) == before


def test_transient_enrollment_retry_reuses_identity(courses, database, learner, monkeypatch):
    original, identities = courses._detail, []
    def retry(course, user, session):
        result = original(course, user, session)
        identities.append(database.enrollments.find_one(session=session)["_id"])
        if len(identities) == 1:
            raise OperationFailure("Injected transient failure", 112, {"errorLabels": ["TransientTransactionError"]})
        return result
    monkeypatch.setattr(courses, "_detail", retry)
    assert courses.enroll_in_course("demo-open", learner)["isEnrolled"]
    assert len(identities) == 2 and identities[0] == identities[1]
    assert database.enrollments.count_documents({}) == 1


def test_missing_user_cannot_create_orphan_enrollment(courses, database, learner):
    learner["id"] = str(uuid4())
    with pytest.raises(HTTPException) as failure:
        courses.enroll_in_course("demo-open", learner)
    assert failure.value.status_code == 404 and database.enrollments.count_documents({}) == 0


def test_admin_invited_mongo_only_account_can_read_and_enroll(learner_http, database):
    admin = MongoAdminService(database)
    invited = admin.add_course_attendees("demo-open", [{"email": "new-only-mongo@learnova.example", "name": "Invited learner",
        "enrollmentSource": "invited", "paymentStatus": "not_required"}])["attendees"][0]
    learner_http.headers.update(bearer(invited["userId"], role="learner", email="new-only-mongo@learnova.example"))
    assert learner_http.get("/courses/demo-open/content/demo-image").status_code == 200
    assert learner_http.post("/courses/demo-open/enroll").json()["isEnrolled"]
    assert admin.list_course_attendees("demo-open")["attendees"][0]["userId"] == invited["userId"]


@pytest.mark.parametrize("path,payload", [
    ("/courses/demo-payment/payments/order", None),
    ("/courses/demo-payment/payments/verify", {"razorpayOrderId": "order_test", "razorpayPaymentId": "pay_test", "razorpaySignature": "test_signature"}),
])
def test_later_phase_writes_are_explicitly_unavailable(learner_http, monkeypatch, path, payload):
    def fail(): raise AssertionError("MongoDB mode must never write to PostgreSQL")
    monkeypatch.setattr("backend.modules.courses.service.connect", fail)
    assert learner_http.post(path, json=payload).status_code == 501


def test_mongo_learner_routes_never_open_postgres(learner_http, monkeypatch):
    def fail(): raise AssertionError("MongoDB learner routes must not open PostgreSQL")
    for module in ("courses", "auth", "admin"):
        monkeypatch.setattr(f"backend.modules.{module}.service.connect", fail)
    assert learner_http.get("/courses").status_code == 200
    assert learner_http.get("/courses/demo-open").status_code == 200
    assert learner_http.get("/courses/demo-open/reviews").status_code == 200
    assert learner_http.post("/courses/demo-open/enroll").status_code == 200
    assert learner_http.get("/courses/demo-open/content/demo-image").status_code == 200
    assert learner_http.get("/courses/demo-open/quizzes/demo-quiz").status_code == 403


def test_database_failure_is_sanitized_and_has_cors(learner_http, monkeypatch):
    from pymongo.synchronous.collection import Collection
    original = Collection.find_one
    def unavailable(self, *args, **kwargs):
        if self.name == "courses":
            raise OperationFailure("private server diagnostic")
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Collection, "find_one", unavailable)
    response = learner_http.get("/courses/demo-open", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 503 and "private" not in response.text
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


@pytest.mark.parametrize("auth,admin,mode", [("postgres", "postgres", "mongo"), ("mongo", "postgres", "mongo"), ("mongo", "mongo", "invalid")])
def test_inconsistent_courses_mode_rejected(database, monkeypatch, auth, admin, mode):
    for key, value in {"AUTH_STORAGE": auth, "ADMIN_STORAGE": admin, "COURSES_STORAGE": mode, "MONGODB_DB": database.name}.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(ValueError, match="learner storage|COURSES_STORAGE"):
        with TestClient(app): pass


def test_selected_courses_mode_stays_frozen(learner_http, monkeypatch):
    monkeypatch.setenv("COURSES_STORAGE", "postgres")
    def fail(): raise AssertionError("Selection must remain MongoDB until restart")
    monkeypatch.setattr("backend.modules.courses.service.connect", fail)
    assert learner_http.get("/courses").status_code == 200


def test_catalog_and_detail_queries_are_batched(database, learner):
    class Queries(monitoring.CommandListener):
        def __init__(self): self.names = []
        def started(self, event):
            if event.database_name == database.name and event.command_name in {"find", "aggregate", "getMore"}:
                self.names.append(event.command_name)
        def succeeded(self, event): pass
        def failed(self, event): pass
    listener = Queries()
    with MongoClient(get_mongo_settings().uri, tz_aware=True, timeoutMS=5000, event_listeners=[listener]) as client:
        service = MongoCourseService(client[database.name])
        def count(callback):
            listener.names.clear()
            callback()
            return len(listener.names)
        catalog_before = count(lambda: service.list_courses_for_user(learner))
        detail_before = count(lambda: service.get_course_detail_for_user("demo-open", learner))
        template = database.courses.find_one({"slug": "demo-open"})
        for number in range(10):
            cloned = deepcopy(template)
            cloned.update(_id=str(uuid4()), slug=f"batch-course-{number}", title=f"Batch course {number}",
                          tags=[{**tag, "id": str(uuid4())} for tag in template["tags"]])
            database.courses.insert_one(cloned)
        template = database.course_content.find_one({"slug": "demo-video"})
        for order in range(5, 25):
            cloned = deepcopy(template)
            cloned.update(_id=str(uuid4()), slug=f"batch-content-{order}", display_order=order)
            database.course_content.insert_one(cloned)
        assert count(lambda: service.list_courses_for_user(learner)) == catalog_before == 6
        assert count(lambda: service.get_course_detail_for_user("demo-open", learner)) == detail_before == 8
