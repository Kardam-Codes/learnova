"""Phase 9 report compatibility; execution deliberately deferred by the user."""
from uuid import uuid4

from fastapi import HTTPException
import pytest

from backend.db.mongo.seed import STAMP, fixture_id
from backend.modules.admin.mongo_service import MongoAdminService
from backend.tests.test_mongo_admin import admin_http


def enroll(database, **changes):
    row = {"_id": str(uuid4()), "schema_version": 1, "course_id": fixture_id("course-open"),
           "user_id": fixture_id("learner"), "enrolled_at": STAMP,
           "enrollment_source": "self", "payment_status": "not_required", **changes}
    database.enrollments.insert_one(row)
    return row


def test_report_missing_progress_matches_sql_null_summary_and_filter(database):
    enroll(database)
    admin = MongoAdminService(database)
    report = admin.get_reporting_course_progress()
    assert [card["value"] for card in report["summary"]] == [1, 0, 0, 0]
    assert report["rows"][0]["status"] == "yet_to_start"
    assert report["rows"][0]["completionPercentage"] == "0%"
    assert report["rows"][0]["timeSpent"] == "0:00"
    assert admin.get_reporting_course_progress("yet_to_start")["rows"] == []


def test_report_content_sum_is_not_multiplied_and_summary_is_unfiltered(database):
    enroll(database)
    enroll(database, course_id=fixture_id("course-payment"), payment_status="paid")
    database.course_progress.insert_one({"_id": str(uuid4()), "schema_version": 1,
        "course_id": fixture_id("course-open"), "user_id": fixture_id("learner"),
        "status": "in_progress", "completion_percentage": 33.33,
        "completed_count": 1, "incomplete_count": 2,
        "started_at": STAMP, "completed_at": None, "current_content_id": None, "updated_at": STAMP})
    for mode, position in (("video", 61), ("document", 64)):
        database.content_progress.insert_one({"_id": str(uuid4()), "schema_version": 1,
            "content_id": fixture_id("content-" + mode), "course_id": fixture_id("course-open"),
            "user_id": fixture_id("learner"), "status": "in_progress", "last_position": position,
            "completed_at": None, "updated_at": STAMP})
    result = MongoAdminService(database).get_reporting_course_progress("IN_PROGRESS")
    assert result["activeFilter"] == "in_progress"
    assert [card["value"] for card in result["summary"]] == [2, 0, 1, 0]
    assert len(result["rows"]) == 1
    assert result["rows"][0]["timeSpent"] == "2:05"
    assert result["rows"][0]["completionPercentage"] == "33%"


def test_report_bad_filter_is_400(database):
    with pytest.raises(HTTPException) as error:
        MongoAdminService(database).get_reporting_course_progress("unknown")
    assert error.value.status_code == 400


def test_report_rows_keep_enrollment_without_content(database):
    enroll(database)
    database.course_content.delete_many({})
    assert len(MongoAdminService(database).get_reporting_course_progress()["rows"]) == 1


def test_report_http_uses_selected_mongo_storage(admin_http, database):
    enroll(database)
    response = admin_http.get("/admin/reports/course-progress")
    assert response.status_code == 200
    assert response.json()["summary"][0]["value"] == 1


def test_report_uses_english_name_order_instead_of_binary_order(database):
    database.users.update_one({"_id": fixture_id("learner")}, {"$set": {"name": "alpha"}})
    database.users.update_one({"_id": fixture_id("instructor")}, {"$set": {"name": "Beta"}})
    enroll(database)
    enroll(database, user_id=fixture_id("instructor"))
    rows = MongoAdminService(database).get_reporting_course_progress()["rows"]
    assert [row["participantName"] for row in rows] == ["alpha", "Beta"]
