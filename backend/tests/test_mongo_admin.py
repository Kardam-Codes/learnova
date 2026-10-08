"""Admin API/service tests against guarded real MongoDB databases."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from threading import Barrier
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pymongo.errors import OperationFailure
import pytest

from backend.db.mongo.seed import fixture_id
from backend.main import app
from backend.modules.admin.mongo_service import MongoAdminService, price_to_paise
from backend.modules.admin.schemas import CourseCreateRequest, AdminContentCreateRequest, AdminQuizCreateRequest
from backend.tests.test_mongo_auth import bearer


def course_payload(**changes):
    return CourseCreateRequest(title="New course", shortDescription="Course description", **changes).model_dump()


def lesson_payload(**changes):
    return AdminContentCreateRequest(title="New lesson", contentMode="video", **changes).model_dump()


def quiz_payload():
    return AdminQuizCreateRequest(title="New quiz", maxAttempts=4, questions=[{
        "id": str(uuid4()), "prompt": "Choose the correct answer", "choices": [
            {"id": str(uuid4()), "label": "Correct", "isCorrect": True},
            {"id": str(uuid4()), "label": "Incorrect", "isCorrect": False}]}],
        rewards={"first": 10, "second": 8, "third": 5, "fourthPlus": 2}).model_dump()


@pytest.fixture
def admin(database):
    return MongoAdminService(database)


@pytest.fixture
def admin_http(database, monkeypatch):
    monkeypatch.setenv("AUTH_STORAGE", "mongo")
    monkeypatch.setenv("ADMIN_STORAGE", "mongo")
    monkeypatch.setenv("MONGODB_DB", database.name)
    with TestClient(app) as client:
        client.headers.update(bearer(fixture_id("instructor"), role="instructor", email="instructor@learnova.example"))
        yield client


def test_course_authoring_http(admin_http, database):
    payload = course_payload(tags=["Python", " python ", "Backend"], responsibleUserId=fixture_id("instructor"), price=19.995)
    response = admin_http.post("/admin/courses", json=payload)
    assert response.status_code == 200, response.text
    course = response.json()
    assert course["price"] == 20.0 and course["tags"] == ["Backend", "Python"]
    assert course["createdBy"] == fixture_id("instructor") and course["responsibleName"] == "Demo instructor"
    stored = database.courses.find_one({"_id": course["id"]})
    assert stored["price_paise"] == 2000
    links = deepcopy(stored["tags"])
    assert admin_http.get("/admin/courses/" + course["slug"]).json() == course
    payload["title"] = "Renamed course"
    changed = admin_http.put("/admin/courses/" + course["slug"], json=payload)
    assert changed.status_code == 200 and changed.json()["slug"] == "renamed-course"
    assert database.courses.find_one({"_id": course["id"]})["tags"] == links
    published = admin_http.post("/admin/courses/renamed-course/publish", json={"isPublished": True})
    assert published.status_code == 200 and published.json()["isPublished"]
    deleted = admin_http.delete("/admin/courses/renamed-course")
    assert deleted.json() == {"deleted": True, "slug": "renamed-course"}
    assert database.tags.count_documents({"normalized_name": "python"}) == 1


@pytest.mark.parametrize("price,expected", [(0.1, 10), (19.995, 2000), (99999999.99, 9999999999)])
def test_money_rounding_matches_postgres_numeric(price, expected):
    assert price_to_paise(price) == expected


@pytest.mark.parametrize("price", [float("inf"), float("nan"), -1, 100000000])
def test_invalid_money_rejected(price):
    with pytest.raises(HTTPException) as error:
        price_to_paise(price)
    assert error.value.status_code == 422


def test_course_validation_rolls_back_tags(admin, database):
    before = database.courses.count_documents({})
    with pytest.raises(HTTPException) as error:
        admin.create_admin_course({"id": fixture_id("instructor")}, course_payload(responsibleUserId=str(uuid4()), tags=["Unused"]))
    assert error.value.status_code == 422 and database.courses.count_documents({}) == before
    assert database.tags.find_one({"normalized_name": "unused"}) is None
    with pytest.raises(HTTPException):
        admin.create_admin_course({"id": fixture_id("instructor")}, course_payload(accessRule="payment", price=0))


@pytest.mark.parametrize("mode", ["video", "document", "image"])
def test_lesson_modes_and_attachment_identity(admin_http, database, mode):
    payload = lesson_payload(attachments=[{"label": "Download", "url": "/uploads/example.pdf", "attachmentType": "file"}])
    payload["contentMode"] = mode
    created = admin_http.post("/admin/courses/demo-open/content", json=payload)
    assert created.status_code == 200, created.text
    item = created.json()
    assert item["contentMode"] == mode and item["displayOrder"] == 5
    attachment = item["attachments"][0]
    # Current lesson UI sends no attachment IDs; unchanged metadata still retains identity.
    updated = admin_http.put(f"/admin/content/{item['slug']}?courseSlug=demo-open", json=payload)
    assert updated.status_code == 200 and updated.json()["attachments"][0]["id"] == attachment["id"]
    assert admin_http.get(f"/admin/content/{item['slug']}?courseSlug=demo-open").json() == updated.json()
    assert admin_http.delete(f"/admin/content/{item['slug']}?courseSlug=demo-open").status_code == 200
    assert database.course_content.find_one({"_id": item["id"]}) is None


def test_content_ambiguity_never_updates_wrong_course(admin_http, admin, database):
    one = admin.create_course_content("demo-open", lesson_payload())
    two = admin.create_course_content("demo-payment", lesson_payload())
    assert one["slug"] == two["slug"]
    path = "/admin/content/" + one["slug"]
    assert admin_http.get(path).status_code == 409
    assert admin_http.put(path, json=lesson_payload()).status_code == 409
    assert admin_http.delete(path).status_code == 409
    assert admin_http.get(path + "?courseSlug=demo-payment").json()["id"] == two["id"]
    assert admin_http.delete(path + "?courseSlug=demo-payment").status_code == 200
    assert database.course_content.find_one({"_id": one["id"]}) is not None


def test_invalid_content_modes_and_references(admin_http):
    payload = lesson_payload()
    payload["contentMode"] = "quiz"
    assert admin_http.post("/admin/courses/demo-open/content", json=payload).status_code == 422
    payload["contentMode"] = "video"
    payload["responsibleUserId"] = str(uuid4())
    assert admin_http.post("/admin/courses/demo-open/content", json=payload).status_code == 422


def test_quiz_atomic_creation_identity_and_version(admin_http, database):
    payload = quiz_payload()  # Uses crypto.randomUUID-style temporary IDs like the real editor.
    created = admin_http.post("/admin/courses/demo-open/quizzes", json=payload)
    assert created.status_code == 200, created.text
    quiz = created.json()
    assert quiz["questions"][0]["choices"][0]["isCorrect"]
    stored = database.quizzes.find_one({"_id": quiz["id"]})
    content = database.course_content.find_one({"_id": stored["content_id"]})
    assert content["title"] == stored["title"] and stored["version"] == 1
    update = {key: quiz[key] for key in ("title", "description", "durationLabel", "maxAttempts", "questions", "rewards")}
    unchanged = admin_http.put("/admin/quizzes/" + quiz["id"], json=update)
    assert unchanged.status_code == 200 and unchanged.json() == quiz
    assert database.quizzes.find_one({"_id": quiz["id"]})["version"] == 1
    update["questions"][0]["prompt"] = "Updated question prompt"
    changed = admin_http.put("/admin/quizzes/" + quiz["id"], json=update)
    assert changed.status_code == 200
    assert changed.json()["questions"][0]["id"] == quiz["questions"][0]["id"]
    assert changed.json()["questions"][0]["choices"] == quiz["questions"][0]["choices"]
    assert database.quizzes.find_one({"_id": quiz["id"]})["version"] == 2
    assert admin_http.delete("/admin/quizzes/" + quiz["id"]).status_code == 200
    assert database.course_content.find_one({"_id": stored["content_id"]}) is None


def test_quiz_creation_failure_leaves_no_content(admin, database, monkeypatch):
    before = list(database.course_content.find().sort("_id", 1))
    def fail(document): raise HTTPException(422, "injected assembled document rejection")
    monkeypatch.setattr("backend.modules.admin.mongo_service.bson_size_check", fail)
    with pytest.raises(HTTPException):
        admin.create_course_quiz("demo-open", quiz_payload())
    assert list(database.course_content.find().sort("_id", 1)) == before


def test_quiz_insert_failure_rolls_back_content_and_parent(admin, database, monkeypatch):
    original = admin._questions
    def invalid(*args):
        result = original(*args)
        result[0]["display_order"] = 0  # Actual MongoDB validator rejects after content insertion.
        return result
    monkeypatch.setattr(admin, "_questions", invalid)
    before = database.courses.find_one({"slug": "demo-open"})
    count = database.course_content.count_documents({})
    with pytest.raises(HTTPException) as failure:
        admin.create_course_quiz("demo-open", quiz_payload())
    assert failure.value.status_code == 422
    assert database.course_content.count_documents({}) == count
    assert database.courses.find_one({"slug": "demo-open"}) == before


def test_empty_quiz_is_retained_and_generic_quiz_is_coherent(admin, database):
    payload = quiz_payload()
    payload["questions"] = []
    quiz = admin.create_course_quiz("demo-open", payload)
    assert quiz["questions"] == []
    content = admin.create_course_content("demo-open", {**lesson_payload(), "contentType": "quiz", "contentMode": "quiz"})
    assert database.quizzes.find_one({"content_id": content["id"]})["questions"] == []


def test_repeated_and_foreign_embedded_ids_rejected(admin, database):
    quiz = admin.create_course_quiz("demo-open", quiz_payload())
    payload = quiz_payload()
    payload["questions"][0]["id"] = quiz["questions"][0]["id"]
    with pytest.raises(HTTPException) as error:
        admin.create_course_quiz("demo-payment", payload)
    assert error.value.status_code == 422
    payload = quiz_payload()
    payload["questions"][0]["choices"][1]["id"] = payload["questions"][0]["choices"][0]["id"]
    with pytest.raises(HTTPException):
        admin.create_course_quiz("demo-open", payload)


def test_repeated_or_foreign_attachment_ids_roll_back(admin, database):
    identifier = str(uuid4())
    item = {"id": identifier, "label": "Download", "url": "/uploads/example.pdf", "attachmentType": "file"}
    count = database.course_content.count_documents({})
    with pytest.raises(HTTPException) as failure:
        admin.create_course_content("demo-open", lesson_payload(attachments=[item, item]))
    assert failure.value.status_code == 422
    assert database.course_content.count_documents({}) == count
    first = admin.create_course_content("demo-open", lesson_payload(attachments=[item]))
    item["id"] = first["attachments"][0]["id"]
    with pytest.raises(HTTPException) as failure:
        admin.create_course_content("demo-payment", lesson_payload(attachments=[item]))
    assert failure.value.status_code == 422


def test_concurrent_course_slugs_and_shared_tags(admin, database, monkeypatch):
    barrier = Barrier(2)
    original = admin._transaction
    def synchronized(callback):
        barrier.wait(timeout=10)
        return original(callback)
    monkeypatch.setattr(admin, "_transaction", synchronized)
    with ThreadPoolExecutor(max_workers=2) as pool:
        courses = list(pool.map(lambda _: admin.create_admin_course({"id": fixture_id("instructor")}, course_payload(tags=["Shared"])), (1, 2)))
    assert sorted(c["slug"] for c in courses) == ["new-course", "new-course-2"]
    assert database.tags.count_documents({"normalized_name": "shared"}) == 1


def test_concurrent_content_orders_and_slugs(admin, database, monkeypatch):
    barrier = Barrier(2)
    original = admin._transaction
    def synchronized(callback):
        barrier.wait(timeout=10)
        return original(callback)
    monkeypatch.setattr(admin, "_transaction", synchronized)
    with ThreadPoolExecutor(max_workers=2) as pool:
        items = list(pool.map(lambda _: admin.create_course_content("demo-open", lesson_payload()), (1, 2)))
    assert sorted(c["slug"] for c in items) == ["new-lesson", "new-lesson-2"]
    assert sorted(c["displayOrder"] for c in items) == [5, 6]


def test_reordering_swaps_unique_orders_transactionally(admin, database):
    before = admin.list_course_content("demo-open")["contentItems"]
    identifiers = [item["id"] for item in reversed(before)]
    reordered = admin.reorder_course_content("demo-open", identifiers)
    assert [item["id"] for item in reordered["contentItems"]] == identifiers
    assert [item["displayOrder"] for item in reordered["contentItems"]] == [1, 2, 3, 4]
    with pytest.raises(HTTPException):
        admin.reorder_course_content("demo-open", identifiers[:-1])
    assert [item["id"] for item in admin.list_course_content("demo-open")["contentItems"]] == identifiers


def test_attendees_preserve_paid_access_and_existing_accounts(admin_http, database):
    row = {"email": "learner@learnova.example", "name": "Do not rename", "enrollmentSource": "admin_added", "paymentStatus": "paid"}
    first = admin_http.post("/admin/courses/demo-payment/attendees", json={"attendees": [row]})
    assert first.status_code == 200
    row["paymentStatus"] = "pending"
    second = admin_http.post("/admin/courses/demo-payment/attendees", json={"attendees": [row]})
    assert second.json()["attendees"][0]["paymentStatus"] == "paid"
    assert second.json()["attendees"][0]["name"] == "Demo learner"
    assert database.enrollments.count_documents({"course_id": fixture_id("course-payment")}) == 1
    row["email"] = "invited@learnova.example"
    invited = admin_http.post("/admin/courses/demo-open/attendees", json={"attendees": [row]})
    assert invited.status_code == 200 and database.users.find_one({"email": row["email"]})["role"] == "learner"
    assert len(admin_http.get("/admin/courses/demo-payment/attendees").json()["attendees"]) == 1


def test_admin_permissions_and_mongo_routes_do_not_open_postgres(admin_http, monkeypatch):
    def fail(): raise AssertionError("MongoDB authoring must not open PostgreSQL")
    monkeypatch.setattr("backend.modules.admin.service.connect", fail)
    monkeypatch.setattr("backend.modules.auth.service.connect", fail)
    assert admin_http.get("/admin/users").status_code == 200
    assert admin_http.get("/admin/courses").status_code == 200
    assert admin_http.get("/admin/courses/demo-open/content").status_code == 200
    assert admin_http.get("/admin/courses/demo-open/quizzes").status_code == 200
    assert admin_http.get("/admin/courses", headers=bearer(fixture_id("learner"))).status_code == 403
    admin_http.headers.clear()
    assert admin_http.get("/admin/courses").status_code == 401


@pytest.fixture
def learner_history(database):
    stamp = datetime.now(timezone.utc)
    course, quiz, content, user = map(fixture_id, ("course-open", "quiz", "content-quiz", "learner"))
    common = {"schema_version": 1, "course_id": course, "user_id": user}
    attempt = str(uuid4())
    documents = {
        "quiz_attempts": {**common, "_id": attempt, "quiz_id": quiz, "content_id": content,
            "quiz_version": 1, "attempt_number": 1, "score": 100.0, "points_earned": 10,
            "submitted_at": stamp, "answers": [{"id": str(uuid4()), "question_id": fixture_id("question"),
                "selected_option_id": fixture_id("option-yes"), "is_correct": True}]},
        "quiz_attempt_counters": {"_id": str(uuid4()), "schema_version": 1, "quiz_id": quiz,
            "user_id": user, "attempts_used": 1, "updated_at": stamp},
        "learner_points": {"_id": str(uuid4()), "schema_version": 1, "user_id": user,
            "total_points": 10, "current_badge": "Newbie", "updated_at": stamp},
        "point_events": {**common, "_id": str(uuid4()), "quiz_id": quiz, "attempt_id": attempt,
            "points_delta": 10, "reason": "Quiz completion", "created_at": stamp},
        "course_progress": {**common, "_id": str(uuid4()), "completion_percentage": 50.0,
            "completed_count": 1, "incomplete_count": 3, "current_content_id": content,
            "status": "in_progress", "updated_at": stamp},
        "content_progress": {**common, "_id": str(uuid4()), "content_id": content,
            "status": "completed", "last_position": 30, "completed_at": stamp, "updated_at": stamp},
        "enrollments": {**common, "_id": str(uuid4()), "enrolled_at": stamp,
            "enrollment_source": "admin_added", "payment_status": "paid"},
        "reviews": {**common, "_id": str(uuid4()), "rating": 5, "comment": "Helpful",
            "created_at": stamp, "updated_at": stamp},
        "payment_orders": {**common, "_id": str(uuid4()), "provider": "razorpay",
            "provider_order_id": "order_" + str(uuid4()), "amount_paise": 9900,
            "currency": "INR", "status": "paid", "created_at": stamp},
    }
    for name, row in documents.items():
        database[name].insert_one(row)
    return {name: database[name].find_one({"_id": row["_id"]}) for name, row in documents.items()}


@pytest.mark.parametrize("target", ["course", "content", "quiz"])
def test_deletion_matrix_preserves_awarded_points(admin, database, learner_history, target):
    user_before = list(database.users.find().sort("_id", 1))
    tags_before = list(database.tags.find().sort("_id", 1))
    if target == "course":
        admin.delete_admin_course("demo-open")
    elif target == "content":
        admin.delete_course_content("demo-quiz", course_slug="demo-open")
    else:
        admin.delete_quiz_detail(fixture_id("quiz"))
    for name in ("quizzes", "quiz_attempts", "quiz_attempt_counters", "content_progress"):
        assert database[name].count_documents({}) == 0
    assert database.course_content.find_one({"_id": fixture_id("content-quiz")}) is None
    assert database.learner_points.find_one() == learner_history["learner_points"]
    event = database.point_events.find_one()
    assert event["points_delta"] == 10 and event["quiz_id"] is None and "attempt_id" not in event
    assert list(database.users.find().sort("_id", 1)) == user_before
    assert list(database.tags.find().sort("_id", 1)) == tags_before
    assert database.courses.find_one({"slug": "demo-payment"}) is not None
    if target == "course":
        for name in ("course_content", "course_progress", "enrollments", "reviews", "payment_orders"):
            assert database[name].count_documents({}) == 0
        assert event["course_id"] is None
    else:
        assert event["course_id"] == fixture_id("course-open")
        progress = database.course_progress.find_one()
        assert progress["current_content_id"] is None
        # Keep historical summary values, matching the current SQL SET NULL behavior.
        assert progress["completion_percentage"] == 50.0 and progress["completed_count"] == 1
        for name in ("enrollments", "reviews", "payment_orders"):
            assert database[name].find_one() == learner_history[name]


def test_course_deletion_failure_rolls_back_every_collection(admin, database, learner_history, monkeypatch):
    before = {name: list(database[name].find().sort("_id", 1)) for name in database.list_collection_names()}
    original = admin._delete_contents
    def fail_after_deleting(*args):
        original(*args)
        raise HTTPException(409, "Injected failure after dependent deletions")
    monkeypatch.setattr(admin, "_delete_contents", fail_after_deleting)
    with pytest.raises(HTTPException):
        admin.delete_admin_course("demo-open")
    after = {name: list(database[name].find().sort("_id", 1)) for name in database.list_collection_names()}
    assert after == before


def test_quiz_definition_edit_retains_historical_answers(admin, database, learner_history):
    quiz = admin.get_quiz_detail(fixture_id("quiz"))
    payload = {key: quiz[key] for key in ("title", "description", "durationLabel", "maxAttempts", "questions", "rewards")}
    payload["questions"] = []
    assert admin.update_quiz_detail(quiz["id"], payload)["questions"] == []
    assert database.quizzes.find_one()["version"] == 2
    for name in ("quiz_attempts", "quiz_attempt_counters", "point_events", "learner_points"):
        assert database[name].find_one() == learner_history[name]


def test_content_conversion_requires_explicit_history_decision(admin, database, learner_history):
    before = database.course_content.find_one({"_id": fixture_id("content-quiz")})
    with pytest.raises(HTTPException) as failure:
        admin.update_course_content("demo-quiz", lesson_payload(), course_slug="demo-open")
    assert failure.value.status_code == 409
    assert database.course_content.find_one({"_id": before["_id"]}) == before
    assert database.quiz_attempts.find_one() == learner_history["quiz_attempts"]


def test_oversize_course_rejected_without_partial_tags(admin, database):
    before = database.courses.count_documents({})
    payload = course_payload(description="x" * (16 * 1024 * 1024), tags=["Oversize"])
    with pytest.raises(HTTPException) as failure:
        admin.create_admin_course({"id": fixture_id("instructor")}, payload)
    assert failure.value.status_code == 422
    assert database.courses.count_documents({}) == before
    assert database.tags.find_one({"normalized_name": "oversize"}) is None


def test_oversize_tag_rejected_before_course_commit(admin, database):
    before = database.tags.count_documents({})
    with pytest.raises(HTTPException) as failure:
        admin.create_admin_course({"id": fixture_id("instructor")}, course_payload(tags=["x" * (16 * 1024 * 1024)]))
    assert failure.value.status_code == 422
    assert database.tags.count_documents({}) == before


def test_unrepresentable_quiz_integer_rolls_back_content(admin, database):
    before = database.course_content.count_documents({})
    payload = quiz_payload()
    payload["maxAttempts"] = 2 ** 80
    with pytest.raises(HTTPException) as failure:
        admin.create_course_quiz("demo-open", payload)
    assert failure.value.status_code == 422
    assert database.course_content.count_documents({}) == before


def test_upload_and_content_deletion_keep_external_file(admin_http, database, tmp_path, monkeypatch):
    monkeypatch.setattr("backend.modules.admin.service.UPLOADS_ROOT", tmp_path)
    uploaded = admin_http.post("/admin/uploads", data={"category": "attachments"},
        files={"file": ("notes.pdf", b"%PDF-test", "application/pdf")})
    assert uploaded.status_code == 200
    files = list(tmp_path.rglob("*.pdf"))
    assert len(files) == 1 and files[0].read_bytes() == b"%PDF-test"
    created = admin_http.post("/admin/courses/demo-open/content", json=lesson_payload(
        attachments=[{"label": "Notes", "url": uploaded.json()["url"], "attachmentType": "file"}])).json()
    assert admin_http.delete(f"/admin/content/{created['slug']}?courseSlug=demo-open").status_code == 200
    assert files[0].is_file()


def test_concurrent_child_creation_and_course_delete_never_orphan(admin, database, monkeypatch):
    barrier = Barrier(2)
    original = admin._transaction
    def synchronized(callback):
        barrier.wait(timeout=10)
        return original(callback)
    monkeypatch.setattr(admin, "_transaction", synchronized)
    def create():
        try:
            admin.create_course_content("demo-open", lesson_payload())
            return 200
        except HTTPException as failure:
            return failure.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        child = pool.submit(create)
        deletion = pool.submit(admin.delete_admin_course, "demo-open")
        assert deletion.result()["deleted"]
        assert child.result() in (200, 404)
    assert database.course_content.count_documents({"course_id": fixture_id("course-open")}) == 0
    assert database.quizzes.count_documents({"course_id": fixture_id("course-open")}) == 0


@pytest.mark.parametrize("auth,admin_mode", [("postgres", "mongo"), ("mongo", "invalid")])
def test_inconsistent_admin_mode_rejected(database, monkeypatch, auth, admin_mode):
    monkeypatch.setenv("AUTH_STORAGE", auth)
    monkeypatch.setenv("ADMIN_STORAGE", admin_mode)
    monkeypatch.setenv("MONGODB_DB", database.name)
    with pytest.raises(ValueError, match="ADMIN_STORAGE|admin storage"):
        with TestClient(app):
            pass


def test_admin_database_failure_is_sanitized_without_postgres_fallback(admin_http, monkeypatch):
    from pymongo.synchronous.collection import Collection
    original = Collection.find_one
    def unavailable(self, *args, **kwargs):
        if self.name == "courses":
            raise OperationFailure("private server diagnostic")
        return original(self, *args, **kwargs)
    def fail(): raise AssertionError("Must not fall back to PostgreSQL")
    monkeypatch.setattr(Collection, "find_one", unavailable)
    monkeypatch.setattr("backend.modules.admin.service.connect", fail)
    response = admin_http.get("/admin/courses/demo-open")
    assert response.status_code == 503
    assert "private" not in response.text and "MongoDB" in response.text
