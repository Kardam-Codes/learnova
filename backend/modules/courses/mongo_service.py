"""MongoDB learner access, enrollment, progress, and reviews; later writes are guarded."""
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from functools import wraps
import re
from uuid import uuid4

from fastapi import HTTPException
import pymongo
from pymongo.errors import DocumentTooLarge, DuplicateKeyError, PyMongoError, WriteError

from backend.db.mongo.transactions import lock_course, run_transaction
from backend.db.mongo.quiz_schema import require_quiz_receipts
from backend.modules.courses.mongo_progress import recalculate_course_progress
from backend.modules.courses.mongo_quiz import (
    allocate_attempt, award_points, digest, normalize_answers, quiz_fingerprint, reward_for_attempt, score_answers,
)
from backend.modules.courses.service import BADGE_TIERS, _apply_content_locks


def learner_errors(function):
    @wraps(function)
    def wrapped(self, *args, **kwargs):
        try:
            with pymongo.timeout(self.database.client.options.timeout or 5.0):
                return function(self, *args, **kwargs)
        except DuplicateKeyError:
            raise HTTPException(409, "Concurrent learner update conflict. Reload and retry.") from None
        except (DocumentTooLarge, OverflowError):
            raise HTTPException(422, "Learner data exceeds the supported document or integer size.") from None
        except WriteError as error:
            if error.code == 121:
                raise HTTPException(422, "Learner data does not satisfy the reviewed storage schema.") from None
            raise HTTPException(503, "MongoDB learner storage is unavailable.") from None
        except PyMongoError:
            raise HTTPException(503, "MongoDB learner storage is unavailable.") from None
    return wrapped


def is_enrolled(enrollment):
    return bool(enrollment) and enrollment["payment_status"] in {"paid", "not_required"}


def price(course):
    return float(Decimal(course["price_paise"]) / 100)


def now():
    return datetime.now(timezone.utc)


class MongoCourseService:
    def __init__(self, database):
        self.database = database

    def _transaction(self, callback):
        return run_transaction(self.database, callback)

    def _course(self, slug, session=None, *, published_only=True):
        query = {"slug": slug}
        if published_only:
            query["is_published"] = True
        course = self.database.courses.find_one(query, session=session)
        if course is None:
            raise HTTPException(404, "Course not found.")
        return course

    def _enrollment(self, course_id, user_id, session=None):
        return self.database.enrollments.find_one({"course_id": course_id, "user_id": user_id}, session=session)

    def _require_learning_access(self, course_id, user, session):
        if self.database.users.find_one({"_id": user["id"]}, {"_id": 1}, session=session) is None:
            raise HTTPException(404, "User not found.")
        if not is_enrolled(self._enrollment(course_id, user["id"], session)):
            raise HTTPException(403, "Enroll in this course before accessing the learning content.")

    def _profile(self, user):
        points = self.database.learner_points.find_one({"user_id": user["id"]})
        return {"learnerName": user["name"], "totalPoints": points["total_points"] if points else 0,
                "currentBadge": points["current_badge"] if points else "Newbie", "badgeTiers": BADGE_TIERS}

    @learner_errors
    def list_courses_for_user(self, user):
        courses = list(self.database.courses.find({"is_published": True}).sort("title", 1))
        identifiers = [course["_id"] for course in courses]
        scoped = {"user_id": user["id"], "course_id": {"$in": identifiers}}
        enrollments = {row["course_id"]: row for row in self.database.enrollments.find(scoped)}
        progress = {row["course_id"]: row for row in self.database.course_progress.find(scoped)}
        content_progress = {row["content_id"]: row["status"] for row in self.database.content_progress.find(
            scoped, {"content_id": 1, "status": 1})}
        content = defaultdict(list)
        for row in self.database.course_content.find({"course_id": {"$in": identifiers}},
            {"course_id": 1, "slug": 1, "content_mode": 1, "display_order": 1}).sort("display_order", 1):
            content[row["course_id"]].append(row)
        enrolled_courses, available_courses = [], []
        for course in courses:
            enrollment = enrollments.get(course["_id"])
            summary = progress.get(course["_id"], {})
            items = content[course["_id"]]
            first = items[0] if items else {}
            # Preserve the SQL preference: in-progress, then unstarted, then completed.
            last = min(items, key=lambda item: (
                0 if content_progress.get(item["_id"]) == "in_progress" else 1,
                1 if content_progress.get(item["_id"]) == "completed" else 0,
                item["display_order"])) if items else {}
            current = next((item for item in items if item["_id"] == summary.get("current_content_id")), {})
            paid = course["access_rule"] == "payment"
            payment_status = enrollment["payment_status"] if enrollment else "pending" if paid else "not_required"
            enrolled = is_enrolled(enrollment)
            status = summary.get("status", "yet_to_start")
            payload = {"id": course["slug"], "title": course["title"], "shortDescription": course["short_description"],
                "coverImage": course.get("thumbnail_url") or course.get("cover_image_url"),
                "tags": sorted((tag["name"] for tag in course["tags"]), key=str.casefold),
                "isPaid": paid, "price": price(course), "accessRule": course["access_rule"],
                "paymentStatus": payment_status, "isPurchased": payment_status == "paid" if paid else enrolled,
                "isEnrolled": enrolled, "isLoggedIn": True, "hasStarted": enrolled and status != "yet_to_start",
                "isInProgress": enrolled and status == "in_progress", "detailPath": "/courses/" + course["slug"],
                "firstContentId": first.get("slug"), "firstContentMode": first.get("content_mode"),
                "lastContentId": current.get("slug") or last.get("slug") or first.get("slug"),
                # Existing SQL chooses this mode from the preferred item, even with a resume pointer.
                "lastContentMode": last.get("content_mode") or first.get("content_mode")}
            (enrolled_courses if enrolled else available_courses).append(payload)
        return {"profile": self._profile(user), "courses": enrolled_courses, "enrolledCourses": enrolled_courses,
                "availableCourses": available_courses}

    @staticmethod
    def _learner_quiz(quiz):
        # SQL inner joins omit questions without options and wholly empty definitions.
        questions = []
        for question in sorted(quiz["questions"], key=lambda item: item["display_order"]):
            options = sorted(question["options"], key=lambda item: item["display_order"])
            if options:
                questions.append({"id": question["id"], "prompt": question["question_text"],
                    "options": [option["option_text"] for option in options],
                    "allowsMultipleAnswers": sum(option["is_correct"] for option in options) > 1})
        if not questions:
            return {}
        result = {"quizQuestions": questions, "quizRules": {"totalQuestions": len(questions), "maxAttempts": quiz["max_attempts"]}}
        if quiz["reward_rules"]:
            first = next((rule["points_awarded"] for rule in quiz["reward_rules"] if rule["attempt_number"] == 1), 0)
            result["reward"] = {"pointsEarned": first, "nextTarget": 100, "message": "Reach the next rank to gain more points."}
        return result

    def _content_items(self, course_id, user_id, session=None):
        rows = list(self.database.course_content.find({"course_id": course_id}, session=session).sort("display_order", 1))
        progress = {row["content_id"]: row["status"] for row in self.database.content_progress.find(
            {"course_id": course_id, "user_id": user_id}, {"content_id": 1, "status": 1}, session=session)}
        quizzes = {quiz["content_id"]: quiz for quiz in self.database.quizzes.find(
            {"course_id": course_id, "content_id": {"$in": [row["_id"] for row in rows]}}, session=session)}
        return [{"id": row["slug"], "title": row["title"], "type": row["content_type"], "mode": row["content_mode"],
            "status": progress.get(row["_id"], "not_started"), "order": row["display_order"],
            "duration": row.get("duration_label"), "description": row.get("description"), "contentUrl": row.get("content_url"),
            "attachments": [{"id": item["id"], "label": item["label"], "url": item["url"]} for item in row["attachments"]],
            "nextContentId": rows[index + 1]["slug"] if index + 1 < len(rows) else None,
            **(self._learner_quiz(quizzes[row["_id"]]) if row["_id"] in quizzes else {})}
            for index, row in enumerate(rows)]

    def _reviews(self, course, user, enrolled, session=None):
        rows = list(self.database.reviews.find({"course_id": course["_id"]}, session=session).sort([("created_at", 1), ("_id", 1)]))
        references = {row["user_id"] for row in rows} | {course.get("responsible_user_id")}
        users = {row["_id"]: row for row in self.database.users.find({"_id": {"$in": list(references - {None})}},
            {"name": 1}, session=session)}
        rows = [row for row in rows if row["user_id"] in users]
        own = next((row for row in rows if row["user_id"] == user["id"]), {})
        return {"averageRating": round(sum(row["rating"] for row in rows) / len(rows), 1) if rows else 0,
            "totalReviews": len(rows), "isEnrolled": enrolled,
            "items": [{"id": row["_id"], "authorName": users[row["user_id"]]["name"], "rating": row["rating"],
                       "comment": row["comment"]} for row in rows], "learnerDraft": own.get("comment", "")}, users

    def _detail(self, course, user, session=None):
        enrollment = self._enrollment(course["_id"], user["id"], session)
        enrolled = is_enrolled(enrollment)
        content = _apply_content_locks(self._content_items(course["_id"], user["id"], session), enrolled)
        summary = self.database.course_progress.find_one({"course_id": course["_id"], "user_id": user["id"]}, session=session) or {}
        reviews, users = self._reviews(course, user, enrolled, session)
        total, completed = len(content), summary.get("completed_count", 0)
        return {"id": course["slug"], "title": course["title"], "shortDescription": course["short_description"],
            "thumbnail": course.get("thumbnail_url"), "coverImage": course.get("cover_image_url"),
            "providerName": users.get(course.get("responsible_user_id"), {}).get("name") or "Learnova",
            "learnerName": user["name"], "price": price(course), "isEnrolled": enrolled,
            "paymentStatus": enrollment["payment_status"] if enrollment else "pending" if course["access_rule"] == "payment" else "not_required",
            "accessRule": course["access_rule"], "canEnrollFree": course["access_rule"] == "open" and not enrolled,
            "requiresPayment": course["access_rule"] == "payment" and not enrolled,
            "progress": {"completionPercentage": summary.get("completion_percentage", 0) or 0.0,
                         "totalCount": total, "completedCount": completed,
                         "incompleteCount": summary.get("incomplete_count") or max(total - completed, 0)},
            "contentItems": content, "reviews": reviews}

    @learner_errors
    def get_course_detail_for_user(self, course_slug, user):
        return self._detail(self._course(course_slug), user)

    @learner_errors
    def get_course_reviews_for_user(self, course_slug, user):
        # Preserve the legacy reviews endpoint: missing/unpublished courses do not 404.
        course = self.database.courses.find_one({"slug": course_slug})
        if course is None:
            return {"averageRating": 0, "totalReviews": 0, "isEnrolled": False, "items": [], "learnerDraft": ""}
        enrollment = self._enrollment(course["_id"], user["id"]) if course["is_published"] else None
        return self._reviews(course, user, is_enrolled(enrollment))[0]

    @learner_errors
    def get_course_content_for_user(self, course_slug, content_slug, user):
        course = self._course(course_slug)
        if not is_enrolled(self._enrollment(course["_id"], user["id"])):
            raise HTTPException(403, "Enroll in this course before accessing the learning content.")
        items = _apply_content_locks(self._content_items(course["_id"], user["id"]), True)
        item = next((item for item in items if item["id"] == content_slug), None)
        if item is None:
            raise HTTPException(404, "Content not found.")
        if item["isLocked"]:
            raise HTTPException(403, item["lockReason"])
        # Direct player responses historically omit overview-only locking fields.
        item.pop("isLocked")
        item.pop("lockReason")
        return {"courseId": course["slug"], "courseTitle": course["title"], "contentItem": item}

    @learner_errors
    def get_quiz_for_user(self, course_slug, content_slug, user):
        result = self.get_course_content_for_user(course_slug, content_slug, user)
        if result["contentItem"]["mode"] != "quiz":
            raise HTTPException(400, "Requested content is not a quiz.")
        return result

    @learner_errors
    def enroll_in_course(self, course_slug, user):
        identifier, stamp = str(uuid4()), datetime.now(timezone.utc)
        def enroll(session):
            course = self._course(course_slug, session)
            course = lock_course(self.database, course["_id"], session)
            if self.database.users.find_one({"_id": user["id"]}, {"_id": 1}, session=session) is None:
                raise HTTPException(404, "User not found.")
            enrollment = self._enrollment(course["_id"], user["id"], session)
            if not is_enrolled(enrollment):
                if course["access_rule"] == "payment":
                    raise HTTPException(400, "This course requires payment before enrollment.")
                if course["access_rule"] == "invitation":
                    raise HTTPException(403, "This course can only be accessed by invited learners.")
                self.database.enrollments.update_one({"course_id": course["_id"], "user_id": user["id"]}, {
                    "$set": {"enrollment_source": "self", "payment_status": "not_required"},
                    "$setOnInsert": {"_id": identifier, "schema_version": 1, "enrolled_at": stamp}}, upsert=True, session=session)
            return self._detail(course, user, session)
        return self._transaction(enroll)

    def _recalculate_course_progress(self, course_id, user_id, content_id, session, *, stamp, identifier):
        return recalculate_course_progress(self.database, course_id, user_id, content_id, session,
                                           stamp=stamp, identifier=identifier)

    @learner_errors
    def update_content_progress_for_user(self, course_slug, content_slug, user, *, status_value, last_position):
        if status_value not in {"not_started", "in_progress", "completed"} or not isinstance(last_position, int) or last_position < 0:
            raise HTTPException(422, "Invalid progress status or position.")
        identifier, summary_identifier, stamp = str(uuid4()), str(uuid4()), now()
        def progress(session):
            course = lock_course(self.database, self._course(course_slug, session)["_id"], session)
            self._require_learning_access(course["_id"], user, session)
            content = self.database.course_content.find_one({"course_id": course["_id"], "slug": content_slug}, session=session)
            if content is None:
                raise HTTPException(404, "Content not found.")
            if content["content_mode"] == "quiz":
                items = _apply_content_locks(self._content_items(course["_id"], user["id"], session), True)
                item = next(item for item in items if item["id"] == content_slug)
                if item["isLocked"]:
                    raise HTTPException(403, item["lockReason"])
                raise HTTPException(400, "Quiz progress must be completed through quiz submission.")
            query = {"content_id": content["_id"], "user_id": user["id"]}
            previous = self.database.content_progress.find_one(query, session=session)
            if previous and previous["course_id"] != course["_id"]:
                raise HTTPException(409, "Existing progress belongs to another course.")
            self.database.content_progress.update_one(query, {
                "$set": {"status": status_value, "last_position": last_position,
                    "completed_at": stamp if status_value == "completed" else None, "updated_at": stamp},
                "$setOnInsert": {"_id": identifier, "schema_version": 1, "course_id": course["_id"]}}, upsert=True, session=session)
            summary = self._recalculate_course_progress(course["_id"], user["id"], content["_id"], session,
                                                       stamp=stamp, identifier=summary_identifier)
            updated = next((item for item in self._content_items(course["_id"], user["id"], session) if item["id"] == content_slug), None)
            if updated is None:
                raise HTTPException(404, "Content not found.")
            return {"courseId": course_slug, "contentItem": updated, "progress": summary}
        return self._transaction(progress)

    @learner_errors
    def submit_course_review(self, course_slug, user, rating, comment):
        if not isinstance(rating, int) or not 1 <= rating <= 5 or not isinstance(comment, str) or not 3 <= len(comment) <= 2000:
            raise HTTPException(422, "Review rating or comment is outside the supported range.")
        identifier, stamp = str(uuid4()), now()
        def review(session):
            course = lock_course(self.database, self._course(course_slug, session)["_id"], session)
            self._require_learning_access(course["_id"], user, session)
            self.database.reviews.update_one({"course_id": course["_id"], "user_id": user["id"]}, {
                "$set": {"rating": rating, "comment": comment, "updated_at": stamp},
                "$setOnInsert": {"_id": identifier, "schema_version": 1, "created_at": stamp}}, upsert=True, session=session)
            return self._reviews(course, user, True, session)[0]
        return self._transaction(review)

    @learner_errors
    def submit_quiz_attempt(self, course_slug, content_slug, user, answers, *, submission_key=None):
        if submission_key is not None and (not isinstance(submission_key, str)
                or not re.fullmatch(r"[\x21-\x7e]{1,128}", submission_key)):
            raise HTTPException(422, "Idempotency-Key must contain 1 to 128 visible ASCII characters.")
        submitted = normalize_answers(answers)
        fingerprint = digest(submitted)
        ids = {name: str(uuid4()) for name in ("attempt", "counter", "content", "summary", "points", "event")}
        answer_ids = {(question, index): str(uuid4()) for question, indexes in submitted.items() for index in indexes}
        stamp = now()
        def submit(session):
            require_quiz_receipts(self.database, session)
            course = self._course(course_slug, session)
            self._require_learning_access(course["_id"], user, session)
            content = self.database.course_content.find_one({"course_id": course["_id"], "slug": content_slug,
                                                            "content_mode": "quiz"}, session=session)
            quiz = self.database.quizzes.find_one({"course_id": course["_id"], "content_id": content["_id"]},
                                                  session=session) if content else None
            if quiz is None:
                raise HTTPException(404, "Quiz not found.")
            if submission_key is not None:
                previous = self.database.quiz_attempts.find_one({"quiz_id": quiz["_id"], "user_id": user["id"],
                                                               "submission_key": submission_key}, session=session)
                if previous:
                    if previous.get("submission_fingerprint") != fingerprint:
                        raise HTTPException(409, "Idempotency-Key was already used with different quiz answers.")
                    if "result_snapshot" not in previous:
                        raise HTTPException(409, "The stored quiz submission has no replay result.")
                    return previous["result_snapshot"]
            course = lock_course(self.database, course["_id"], session)
            items = _apply_content_locks(self._content_items(course["_id"], user["id"], session), True)
            item = next(item for item in items if item["id"] == content_slug)
            if item["isLocked"]:
                raise HTTPException(403, item["lockReason"])
            # Preserve SQL's inner-join question selection until the draft-readiness
            # policy is finalized. Existing empty definitions are never deleted.
            scoring_quiz = {**quiz, "questions": [question for question in quiz["questions"] if question["options"]]}
            score, records = score_answers(scoring_quiz, submitted, answer_ids)
            number = allocate_attempt(self.database, quiz, user["id"], session, stamp=stamp, identifier=ids["counter"])
            points = reward_for_attempt(quiz, number)
            attempt = {"_id": ids["attempt"], "schema_version": 1, "quiz_id": quiz["_id"], "user_id": user["id"],
                "course_id": course["_id"], "content_id": content["_id"], "attempt_number": number, "score": score,
                "points_earned": points, "submitted_at": stamp, "answers": records, "quiz_version": quiz["version"],
                "quiz_fingerprint": quiz_fingerprint(quiz), "question_count": len(scoring_quiz["questions"])}
            if submission_key is not None:
                attempt.update(submission_key=submission_key, submission_fingerprint=fingerprint)
            self.database.quiz_attempts.insert_one(attempt, session=session)
            progress_query = {"content_id": content["_id"], "user_id": user["id"]}
            previous = self.database.content_progress.find_one(progress_query, session=session)
            if previous and previous["course_id"] != course["_id"]:
                raise HTTPException(409, "Existing progress belongs to another course.")
            self.database.content_progress.update_one(progress_query, {"$set": {
                "status": "completed", "last_position": 100, "completed_at": stamp, "updated_at": stamp},
                "$setOnInsert": {"_id": ids["content"], "schema_version": 1, "course_id": course["_id"]}},
                upsert=True, session=session)
            self._recalculate_course_progress(course["_id"], user["id"], content["_id"], session,
                                               stamp=stamp, identifier=ids["summary"])
            balance = award_points(self.database, user["id"], points, session, stamp=stamp, identifier=ids["points"])
            result = {"attemptNumber": number, "score": score, "pointsEarned": points,
                "totalPoints": balance["total_points"], "currentBadge": balance["current_badge"], "nextTarget": 100,
                "message": "Reach the next rank to gain more points."}
            self.database.quiz_attempts.update_one({"_id": ids["attempt"]}, {"$set": {"result_snapshot": result}}, session=session)
            self.database.point_events.insert_one({"_id": ids["event"], "schema_version": 1, "user_id": user["id"],
                "course_id": course["_id"], "quiz_id": quiz["_id"], "attempt_id": ids["attempt"],
                "points_delta": points, "reason": f"Quiz attempt {number} reward", "created_at": stamp}, session=session)
            return result
        return self._transaction(submit)

    @staticmethod
    def create_course_payment_order(*args, **kwargs):
        raise HTTPException(501, "MongoDB checkout will be available after Phase 8.")

    @staticmethod
    def verify_course_payment(*args, **kwargs):
        raise HTTPException(501, "MongoDB payment verification will be available after Phase 8.")
