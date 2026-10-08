"""Shared transaction and parent-course write boundary for domain mutations."""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from pymongo import ReadPreference
from pymongo.errors import DuplicateKeyError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern


def run_transaction(database, callback):
    # The caller supplies an overall pymongo.timeout deadline. Duplicate-key retries
    # need a fresh snapshot; the driver handles transient transaction/commit retries.
    for attempt in range(5):
        try:
            with database.client.start_session() as session:
                return session.with_transaction(callback, read_concern=ReadConcern("snapshot"),
                    write_concern=WriteConcern("majority"), read_preference=ReadPreference.PRIMARY,
                    max_commit_time_ms=5000)
        except DuplicateKeyError:
            if attempt == 4:
                raise


def lock_course(database, course_id, session):
    course = database.courses.find_one({"_id": course_id}, session=session)
    if course is None:
        raise HTTPException(404, "Course not found.")
    # Always change the value, even if two writes start in one BSON millisecond.
    # Admin deletion and learner dependent writes must contend on this same parent.
    stamp = max(datetime.now(timezone.utc), course["updated_at"] + timedelta(milliseconds=1))
    database.courses.update_one({"_id": course_id}, {"$set": {"updated_at": stamp}}, session=session)
    return {**course, "updated_at": stamp}
