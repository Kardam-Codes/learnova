"""Transactional MongoDB course authoring. Reporting remains a later migration phase."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from functools import wraps
import re
from uuid import uuid4

from bson import BSON
from fastapi import HTTPException
import pymongo
from pymongo.errors import DocumentTooLarge, DuplicateKeyError, PyMongoError, WriteError

from backend.config.security import hash_password
from backend.db.mongo.transactions import lock_course, run_transaction
from backend.modules.admin.service import _slugify, _format_duration_label, save_admin_upload


def now():
    return datetime.now(timezone.utc)


def new_id():
    return str(uuid4())


def price_to_paise(value):
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number < 0 or number >= Decimal("100000000"):
            raise ValueError
        # Matches PostgreSQL NUMERIC(10,2) rounding without binary-float multiplication.
        paise = int(number.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) * 100)
        if paise > 9999999999:
            raise ValueError
        return paise
    except (ValueError, InvalidOperation, OverflowError):
        raise HTTPException(422, "Price must be a finite nonnegative amount within the supported range.") from None


def bson_size_check(document):
    if len(BSON.encode(document)) > 16 * 1024 * 1024:
        raise HTTPException(422, "The assembled document exceeds MongoDB's document size limit.")


def admin_errors(function):
    @wraps(function)
    def wrapped(self, *args, **kwargs):
        try:
            with pymongo.timeout(self.database.client.options.timeout or 5.0):
                return function(self, *args, **kwargs)
        except DuplicateKeyError:
            raise HTTPException(409, "Concurrent authoring conflict. Reload and retry.") from None
        except (DocumentTooLarge, OverflowError):
            raise HTTPException(422, "Admin data exceeds the supported document or integer size.") from None
        except WriteError as error:
            if error.code == 121:
                raise HTTPException(422, "Admin data does not satisfy the reviewed storage schema.") from None
            raise HTTPException(503, "MongoDB administration is unavailable.") from None
        except PyMongoError:
            raise HTTPException(503, "MongoDB administration is unavailable.") from None
    return wrapped


class MongoAdminService:
    save_admin_upload = staticmethod(save_admin_upload)

    def __init__(self, database):
        self.database = database

    def _transaction(self, callback):
        return run_transaction(self.database, callback)

    def _course(self, slug, session=None):
        course = self.database.courses.find_one({"slug": slug}, session=session)
        if course is None:
            raise HTTPException(404, "Course not found.")
        return course

    def _lock_course(self, course_id, session):
        return lock_course(self.database, course_id, session)

    def _reference_user(self, identifier, session):
        if identifier and self.database.users.find_one({"_id": identifier}, {"_id": 1}, session=session) is None:
            raise HTTPException(422, "Referenced user does not exist.")

    def _unique_slug(self, collection, title, session, *, course_id=None, exclude=None):
        base = _slugify(title)
        slug, suffix = base, 2
        while True:
            query = {"slug": slug}
            if course_id:
                query["course_id"] = course_id
            if exclude:
                query["_id"] = {"$ne": exclude}
            if self.database[collection].find_one(query, {"_id": 1}, session=session) is None:
                return slug
            slug, suffix = f"{base}-{suffix}", suffix + 1

    def _tags(self, names, existing, session):
        retained = {item["tag_id"]: item for item in existing}
        seen, result = set(), []
        for value in names:
            name = value.strip()
            normalized = name.lower()
            if not name or normalized in seen:
                continue
            seen.add(normalized)
            tag = self.database.tags.find_one({"normalized_name": normalized}, session=session)
            if tag is None:
                tag = {"_id": new_id(), "schema_version": 1, "name": name,
                       "normalized_name": normalized, "created_at": now()}
                self.database.tags.insert_one(tag, session=session)
            old = retained.get(tag["_id"])
            result.append({"id": old["id"] if old else new_id(), "tag_id": tag["_id"], "name": tag["name"]})
        return result

    def _course_fields(self, payload):
        fields = {stored: payload.get(api) for api, stored in (
            ("title", "title"), ("shortDescription", "short_description"), ("description", "description"),
            ("thumbnailUrl", "thumbnail_url"), ("coverImageUrl", "cover_image_url"), ("websiteId", "website_id"),
            ("visibility", "visibility"), ("accessRule", "access_rule"), ("responsibleUserId", "responsible_user_id"))}
        fields.update(price_paise=price_to_paise(payload.get("price", 0)), currency="INR",
                      is_published=payload.get("isPublished", False))
        if fields["access_rule"] == "payment" and fields["price_paise"] == 0:
            raise HTTPException(422, "Payment-access courses require a positive price.")
        return fields

    def _serialize_courses(self, courses, session=None):
        identifiers = [course["_id"] for course in courses]
        references = {c.get(key) for c in courses for key in ("created_by", "responsible_user_id")} - {None}
        users = {u["_id"]: u for u in self.database.users.find({"_id": {"$in": list(references)}},
                        {"name": 1}, session=session)} if references else {}
        contents = defaultdict(list)
        for item in self.database.course_content.find({"course_id": {"$in": identifiers}},
                {"course_id": 1, "duration_label": 1}, session=session):
            contents[item["course_id"]].append(item)
        attendees = Counter(item["course_id"] for item in self.database.enrollments.find(
            {"course_id": {"$in": identifiers}}, {"course_id": 1}, session=session))
        views = Counter(item["course_id"] for item in self.database.course_progress.find(
            {"course_id": {"$in": identifiers}, "status": {"$in": ["in_progress", "completed"]}},
            {"course_id": 1}, session=session))
        result = []
        for course in courses:
            duration = 0
            for item in contents[course["_id"]]:
                label = (item.get("duration_label") or "").lower()
                digits = "".join(re.findall(r"\d", label))
                duration += int(digits or "0") * (2 if "question" in label else 60 if "hour" in label else 1)
            result.append({"id": course["_id"], "slug": course["slug"], "title": course["title"],
                "shortDescription": course["short_description"], "description": course.get("description"),
                "thumbnailUrl": course.get("thumbnail_url"), "coverImageUrl": course.get("cover_image_url"),
                "websiteId": course.get("website_id"), "visibility": course["visibility"],
                "accessRule": course["access_rule"], "price": float(Decimal(course["price_paise"]) / 100),
                "isPublished": course["is_published"], "createdBy": course.get("created_by"),
                "createdByName": users.get(course.get("created_by"), {}).get("name"),
                "responsibleUserId": course.get("responsible_user_id"),
                "responsibleName": users.get(course.get("responsible_user_id"), {}).get("name"),
                "tags": sorted((tag["name"] for tag in course["tags"]), key=str.casefold),
                "attendeeCount": attendees[course["_id"]], "contentCount": len(contents[course["_id"]]),
                "durationMinutes": duration, "durationLabel": _format_duration_label(duration),
                "viewsCount": views[course["_id"]]})
        return result

    @admin_errors
    def list_admin_courses(self, _current_user):
        courses = list(self.database.courses.find().sort([("created_at", -1), ("title", 1)]))
        return {"courses": self._serialize_courses(courses)}

    @admin_errors
    def get_admin_course(self, course_slug):
        return self._serialize_courses([self._course(course_slug)])[0]

    @admin_errors
    def list_admin_users(self, roles=None):
        order = {"super_admin": 0, "admin": 1, "instructor": 2, "learner": 3}
        roles = [role for role in (roles or ["super_admin", "admin", "instructor"]) if role in order]
        roles = roles or ["super_admin", "admin", "instructor"]
        users = list(self.database.users.find({"role": {"$in": roles}},
                     {"name": 1, "email": 1, "role": 1, "is_active": 1}))
        users.sort(key=lambda u: (order[u["role"]], u["name"].casefold()))
        return {"users": [{"id": u["_id"], "name": u["name"], "email": u["email"], "role": u["role"],
                            "isActive": u["is_active"]} for u in users]}

    @admin_errors
    def create_admin_course(self, current_user, payload):
        identifier, stamp = new_id(), now()
        fields = self._course_fields(payload)
        def create(session):
            self._reference_user(current_user["id"], session)
            self._reference_user(fields["responsible_user_id"], session)
            document = {"_id": identifier, "schema_version": 1, **fields,
                "slug": self._unique_slug("courses", payload["title"], session),
                "created_by": current_user["id"], "created_at": stamp, "updated_at": stamp,
                "tags": self._tags(payload.get("tags", []), [], session)}
            bson_size_check(document)
            self.database.courses.insert_one(document, session=session)
            return self._serialize_courses([document], session)[0]
        return self._transaction(create)

    @admin_errors
    def update_admin_course(self, course_slug, payload):
        fields = self._course_fields(payload)
        def update(session):
            course = self._lock_course(self._course(course_slug, session)["_id"], session)
            self._reference_user(fields["responsible_user_id"], session)
            document = {**course, **fields, "slug": self._unique_slug("courses", payload["title"], session, exclude=course["_id"]),
                        "tags": self._tags(payload.get("tags", []), course["tags"], session)}
            bson_size_check(document)
            self.database.courses.replace_one({"_id": course["_id"]}, document, session=session)
            return self._serialize_courses([document], session)[0]
        return self._transaction(update)

    @admin_errors
    def set_course_publish_state(self, course_slug, is_published):
        def publish(session):
            course = self._lock_course(self._course(course_slug, session)["_id"], session)
            course["is_published"] = is_published
            self.database.courses.replace_one({"_id": course["_id"]}, course, session=session)
            return self._serialize_courses([course], session)[0]
        return self._transaction(publish)

    def _content(self, slug, course_slug=None, session=None):
        query = {"slug": slug}
        if course_slug is not None:
            query["course_id"] = self._course(course_slug, session)["_id"]
        matches = list(self.database.course_content.find(query, session=session).limit(2))
        if not matches:
            raise HTTPException(404, "Content not found.")
        if len(matches) != 1:
            raise HTTPException(409, "Content slug is ambiguous. Supply courseSlug.")
        return matches[0]

    def _serialize_content(self, document, session=None):
        course = self.database.courses.find_one({"_id": document["course_id"]}, {"slug": 1}, session=session)
        if course is None:
            raise HTTPException(404, "Course not found.")
        responsible = self.database.users.find_one({"_id": document.get("responsible_user_id")}, {"name": 1}, session=session)
        return {"id": document["_id"], "courseSlug": course["slug"], "slug": document["slug"], "title": document["title"],
            "contentType": document["content_type"], "contentMode": document["content_mode"],
            "description": document.get("description"), "contentUrl": document.get("content_url"),
            "allowDownload": document["allow_download"], "durationLabel": document.get("duration_label"),
            "displayOrder": document["display_order"], "responsibleUserId": document.get("responsible_user_id"),
            "responsibleName": responsible["name"] if responsible else None,
            "attachments": [{"id": item["id"], "label": item["label"], "url": item["url"],
                             "attachmentType": item["attachment_type"]} for item in document["attachments"]]}

    @staticmethod
    def _item_id(value, existing, used):
        identifier = value.get("id")
        if identifier and identifier not in existing:
            identifier = None  # The quiz editor also uses UUIDs for new, unsaved items.
        identifier = identifier or new_id()
        if identifier in used:
            raise HTTPException(422, "Repeated embedded item ID.")
        used.add(identifier)
        return identifier

    def _attachments(self, payload, previous, session):
        existing = {item["id"]: item for item in previous}
        supplied = [item["id"] for item in payload if item.get("id")]
        if len(supplied) != len(set(supplied)):
            raise HTTPException(422, "Repeated attachment ID.")
        novel = [item["id"] for item in payload if item.get("id") and item["id"] not in existing]
        if novel and self.database.course_content.find_one({"attachments.id": {"$in": novel}}, {"_id": 1}, session=session):
            raise HTTPException(422, "An attachment ID belongs to another content item.")
        used, result = set(), []
        for item in payload:
            candidate = dict(item)
            if not candidate.get("id"):
                match = next((old for old in previous if old["id"] not in used and
                    (old["label"], old["url"], old["attachment_type"]) ==
                    (item["label"], item["url"], item["attachmentType"])), None)
                if match:
                    candidate["id"] = match["id"]
            identifier = self._item_id(candidate, existing, used)
            result.append({"id": identifier, "label": item["label"], "url": item["url"],
                           "attachment_type": item["attachmentType"],
                           "created_at": existing.get(identifier, {}).get("created_at", now())})
        return result

    def _content_fields(self, payload, previous, session):
        kind, mode = payload["contentType"], payload["contentMode"]
        if not ((kind == "quiz" and mode == "quiz") or (kind == "lesson" and mode in {"video", "document", "image"})):
            raise HTTPException(422, "Content type and mode do not match.")
        self._reference_user(payload.get("responsibleUserId"), session)
        return {"title": payload["title"], "content_type": kind, "content_mode": mode,
            "description": payload.get("description"), "content_url": payload.get("contentUrl"),
            "allow_download": payload.get("allowDownload", False), "duration_label": payload.get("durationLabel"),
            "responsible_user_id": payload.get("responsibleUserId"),
            "attachments": self._attachments(payload.get("attachments", []), previous, session)}

    def _insert_content(self, course, payload, session):
        last = self.database.course_content.find_one({"course_id": course["_id"]}, sort=[("display_order", -1)], session=session)
        stamp = now()
        content = {"_id": new_id(), "schema_version": 1, "course_id": course["_id"],
                   "slug": self._unique_slug("course_content", payload["title"], session, course_id=course["_id"]),
                   "display_order": last["display_order"] + 1 if last else 1,
                   "created_at": stamp, "updated_at": stamp, **self._content_fields(payload, [], session)}
        bson_size_check(content)
        self.database.course_content.insert_one(content, session=session)
        return content

    @admin_errors
    def create_course_content(self, course_slug, payload):
        def create(session):
            course = self._lock_course(self._course(course_slug, session)["_id"], session)
            content = self._insert_content(course, payload, session)
            if content["content_type"] == "quiz":
                # The generic content endpoint can create a coherent empty quiz draft.
                self.database.quizzes.insert_one({"_id": new_id(), "schema_version": 1,
                    "course_id": course["_id"], "content_id": content["_id"], "title": content["title"],
                    "max_attempts": 4, "version": 1, "questions": [], "reward_rules": [],
                    "created_at": content["created_at"], "updated_at": content["updated_at"]}, session=session)
            return self._serialize_content(content, session)
        return self._transaction(create)

    @admin_errors
    def list_course_content(self, course_slug):
        course = self._course(course_slug)
        documents = self.database.course_content.find({"course_id": course["_id"]}).sort("display_order", 1)
        return {"courseSlug": course_slug, "contentItems": [self._serialize_content(item) for item in documents]}

    @admin_errors
    def get_content_detail(self, content_slug, course_slug=None):
        return self._serialize_content(self._content(content_slug, course_slug))

    @admin_errors
    def update_course_content(self, content_slug, payload, course_slug=None):
        def update(session):
            existing = self._content(content_slug, course_slug, session)
            course = self._lock_course(existing["course_id"], session)
            if existing["content_type"] != payload["contentType"]:
                raise HTTPException(409, "Content type conversion requires a separate deliberate operation.")
            content = {**existing, **self._content_fields(payload, existing["attachments"], session), "updated_at": now(),
                "slug": self._unique_slug("course_content", payload["title"], session,
                                          course_id=course["_id"], exclude=existing["_id"])}
            bson_size_check(content)
            self.database.course_content.replace_one({"_id": content["_id"]}, content, session=session)
            self.database.quizzes.update_one({"content_id": content["_id"]},
                {"$set": {"title": content["title"], "updated_at": now()}}, session=session)
            return self._serialize_content(content, session)
        return self._transaction(update)

    def _quiz(self, identifier, session=None):
        quiz = self.database.quizzes.find_one({"_id": identifier}, session=session)
        if quiz is None:
            raise HTTPException(404, "Quiz not found.")
        return quiz

    def _serialize_quiz(self, quiz, session=None):
        content = self.database.course_content.find_one({"_id": quiz["content_id"]}, session=session)
        course = self.database.courses.find_one({"_id": quiz["course_id"]}, session=session)
        if content is None or course is None:
            raise HTTPException(404, "Quiz content or course not found.")
        rewards = {item["attempt_number"]: item["points_awarded"] for item in quiz["reward_rules"]}
        return {"id": quiz["_id"], "title": quiz["title"], "courseSlug": course["slug"], "contentSlug": content["slug"],
            "description": content.get("description") or "", "durationLabel": content.get("duration_label") or "",
            "maxAttempts": quiz["max_attempts"], "questions": [{"id": q["id"], "prompt": q["question_text"],
                "choices": [{"id": o["id"], "label": o["option_text"], "isCorrect": o["is_correct"]}
                            for o in sorted(q["options"], key=lambda o: o["display_order"])]}
                for q in sorted(quiz["questions"], key=lambda q: q["display_order"]) if q["options"]],
            "rewards": dict(zip(("first", "second", "third", "fourthPlus"), (rewards.get(i, 0) for i in range(1, 5))))}

    def _questions(self, questions, previous, session):
        existing = {q["id"]: q for q in previous}
        old_option_ids = {o["id"] for q in previous for o in q["options"]}
        supplied = [item["id"] for q in questions for item in [q, *q["choices"]] if item.get("id")]
        if len(supplied) != len(set(supplied)):
            raise HTTPException(422, "Repeated question/option ID.")
        novel = set(supplied) - set(existing) - old_option_ids
        if novel and self.database.quizzes.find_one({"$or": [
            {"questions.id": {"$in": list(novel)}}, {"questions.options.id": {"$in": list(novel)}}]}, {"_id": 1}, session=session):
            raise HTTPException(422, "A question/option ID belongs to another quiz.")
        seen, option_seen, result = set(), set(), []
        for order, question in enumerate(questions, 1):
            if question.get("id") in old_option_ids:
                raise HTTPException(422, "A question ID belongs to an option.")
            identifier = self._item_id(question, existing, seen)
            old = existing.get(identifier, {})
            old_options = {o["id"]: o for o in old.get("options", [])}
            if any(choice.get("id") in (old_option_ids - set(old_options)) or choice.get("id") in existing for choice in question["choices"]):
                raise HTTPException(422, "An option ID does not belong to this question.")
            options = [{"id": self._item_id(choice, old_options, option_seen), "option_text": choice["label"],
                        "is_correct": choice.get("isCorrect", False), "display_order": number}
                       for number, choice in enumerate(question["choices"], 1)]
            changed = (old.get("question_text"), old.get("display_order"), old.get("options")) != (question["prompt"], order, options)
            result.append({"id": identifier, "question_text": question["prompt"], "display_order": order,
                "options": options, "created_at": old.get("created_at", now()),
                "updated_at": now() if changed else old["updated_at"]})
        return result

    @staticmethod
    def _rewards(rewards, previous):
        existing = {item["attempt_number"]: item for item in previous}
        return [{"id": existing.get(number, {}).get("id", new_id()), "attempt_number": number, "points_awarded": rewards[key]}
                for number, key in enumerate(("first", "second", "third", "fourthPlus"), 1)]

    @admin_errors
    def create_course_quiz(self, course_slug, payload):
        def create(session):
            course = self._lock_course(self._course(course_slug, session)["_id"], session)
            content = self._insert_content(course, {"title": payload["title"], "contentType": "quiz", "contentMode": "quiz",
                "description": payload.get("description"), "durationLabel": payload.get("durationLabel")}, session)
            quiz = {"_id": new_id(), "schema_version": 1, "course_id": course["_id"], "content_id": content["_id"],
                "title": payload["title"], "max_attempts": payload["maxAttempts"], "version": 1,
                "questions": self._questions(payload["questions"], [], session), "reward_rules": self._rewards(payload["rewards"], []),
                "created_at": now(), "updated_at": now()}
            bson_size_check(quiz)
            self.database.quizzes.insert_one(quiz, session=session)
            return self._serialize_quiz(quiz, session)
        return self._transaction(create)

    @admin_errors
    def list_course_quizzes(self, course_slug):
        course = self._course(course_slug)
        quizzes = self.database.quizzes.find({"course_id": course["_id"]}).sort("created_at", 1)
        return {"courseSlug": course_slug, "quizzes": [self._serialize_quiz(quiz) for quiz in quizzes]}

    @admin_errors
    def get_quiz_detail(self, quiz_id):
        return self._serialize_quiz(self._quiz(quiz_id))

    @admin_errors
    def update_quiz_detail(self, quiz_id, payload):
        def update(session):
            quiz = self._quiz(quiz_id, session)
            course = self._lock_course(quiz["course_id"], session)
            content = self.database.course_content.find_one({"_id": quiz["content_id"]}, session=session)
            if not content or content["course_id"] != course["_id"] or content["content_type"] != "quiz":
                raise HTTPException(409, "Quiz content reference is inconsistent.")
            questions = self._questions(payload["questions"], quiz["questions"], session)
            rewards = self._rewards(payload["rewards"], quiz["reward_rules"])
            changed = questions != quiz["questions"] or rewards != quiz["reward_rules"] or payload["maxAttempts"] != quiz["max_attempts"]
            updated = {**quiz, "title": payload["title"], "max_attempts": payload["maxAttempts"], "questions": questions,
                       "reward_rules": rewards, "version": quiz["version"] + int(changed), "updated_at": now()}
            bson_size_check(updated)
            self.database.quizzes.replace_one({"_id": quiz_id}, updated, session=session)
            self.database.course_content.update_one({"_id": content["_id"]}, {"$set": {
                "title": payload["title"], "description": payload.get("description"), "duration_label": payload.get("durationLabel"),
                "slug": self._unique_slug("course_content", payload["title"], session, course_id=course["_id"], exclude=content["_id"]),
                "updated_at": now()}}, session=session)
            return self._serialize_quiz(updated, session)
        return self._transaction(update)

    def _delete_quizzes(self, identifiers, session):
        if not identifiers:
            return
        attempts = [item["_id"] for item in self.database.quiz_attempts.find({"quiz_id": {"$in": identifiers}}, {"_id": 1}, session=session)]
        self.database.point_events.update_many({"quiz_id": {"$in": identifiers}}, {"$set": {"quiz_id": None}}, session=session)
        if attempts:
            self.database.point_events.update_many({"attempt_id": {"$in": attempts}}, {"$unset": {"attempt_id": ""}}, session=session)
        self.database.quiz_attempts.delete_many({"quiz_id": {"$in": identifiers}}, session=session)
        self.database.quiz_attempt_counters.delete_many({"quiz_id": {"$in": identifiers}}, session=session)
        self.database.quizzes.delete_many({"_id": {"$in": identifiers}}, session=session)

    def _delete_contents(self, identifiers, session):
        quizzes = [q["_id"] for q in self.database.quizzes.find({"content_id": {"$in": identifiers}}, {"_id": 1}, session=session)]
        self._delete_quizzes(quizzes, session)
        self.database.course_progress.update_many({"current_content_id": {"$in": identifiers}},
                                                  {"$set": {"current_content_id": None}}, session=session)
        self.database.content_progress.delete_many({"content_id": {"$in": identifiers}}, session=session)
        self.database.course_content.delete_many({"_id": {"$in": identifiers}}, session=session)

    @admin_errors
    def delete_course_content(self, content_slug, course_slug=None):
        def delete(session):
            content = self._content(content_slug, course_slug, session)
            self._lock_course(content["course_id"], session)
            self._delete_contents([content["_id"]], session)
            return {"deleted": True, "slug": content["slug"]}
        return self._transaction(delete)

    @admin_errors
    def delete_quiz_detail(self, quiz_id):
        def delete(session):
            quiz = self._quiz(quiz_id, session)
            self._lock_course(quiz["course_id"], session)
            self._delete_contents([quiz["content_id"]], session)
            return {"deleted": True, "id": quiz_id}
        return self._transaction(delete)

    @admin_errors
    def delete_admin_course(self, course_slug):
        def delete(session):
            course = self._lock_course(self._course(course_slug, session)["_id"], session)
            contents = [c["_id"] for c in self.database.course_content.find({"course_id": course["_id"]}, {"_id": 1}, session=session)]
            self._delete_contents(contents, session)
            self._delete_quizzes([q["_id"] for q in self.database.quizzes.find({"course_id": course["_id"]}, {"_id": 1}, session=session)], session)
            for name in ("enrollments", "course_progress", "content_progress", "reviews", "payment_orders"):
                self.database[name].delete_many({"course_id": course["_id"]}, session=session)
            self.database.point_events.update_many({"course_id": course["_id"]}, {"$set": {"course_id": None}}, session=session)
            self.database.courses.delete_one({"_id": course["_id"]}, session=session)
            return {"deleted": True, "slug": course["slug"]}
        return self._transaction(delete)

    @admin_errors
    def reorder_course_content(self, course_slug, content_ids):
        def reorder(session):
            course = self._lock_course(self._course(course_slug, session)["_id"], session)
            items = list(self.database.course_content.find({"course_id": course["_id"]}, session=session))
            if len(content_ids) != len(set(content_ids)) or set(content_ids) != {c["_id"] for c in items}:
                raise HTTPException(422, "Reordering must include every course content ID exactly once.")
            # Move beyond every occupied positive order before assigning final 1..N.
            base = max((c["display_order"] for c in items), default=0) + len(items) + 1
            for offset, identifier in enumerate(content_ids):
                self.database.course_content.update_one({"_id": identifier}, {"$set": {"display_order": base + offset}}, session=session)
            for order, identifier in enumerate(content_ids, 1):
                self.database.course_content.update_one({"_id": identifier}, {"$set": {"display_order": order}}, session=session)
            return {"courseSlug": course_slug, "contentItems": [self._serialize_content(
                self.database.course_content.find_one({"_id": identifier}, session=session), session) for identifier in content_ids]}
        return self._transaction(reorder)

    @admin_errors
    def list_course_attendees(self, course_slug):
        course = self._course(course_slug)
        rows = list(self.database.enrollments.find({"course_id": course["_id"]}).sort("enrolled_at", -1))
        users = {u["_id"]: u for u in self.database.users.find({"_id": {"$in": [r["user_id"] for r in rows]}},
                                                          {"name": 1, "email": 1, "role": 1})}
        return {"courseSlug": course_slug, "attendees": [{"id": row["_id"], "userId": row["user_id"],
            "name": users[row["user_id"]]["name"], "email": users[row["user_id"]]["email"], "role": users[row["user_id"]]["role"],
            "enrolledAt": row["enrolled_at"].isoformat(), "enrollmentSource": row["enrollment_source"],
            "paymentStatus": row["payment_status"]} for row in rows if row["user_id"] in users]}

    @admin_errors
    def add_course_attendees(self, course_slug, attendees):
        # Preserve the existing invitation-password contract; hashing stays outside retries.
        password_hash = hash_password("Learnova@123") if attendees else None
        def add(session):
            course = self._lock_course(self._course(course_slug, session)["_id"], session)
            result = []
            for attendee in attendees:
                email = attendee["email"].strip().lower()
                user = self.database.users.find_one({"email": email}, session=session)
                if user is None:
                    stamp = now()
                    user = {"_id": new_id(), "schema_version": 1, "name": attendee["name"], "email": email,
                            "provider": "local", "role": "learner", "is_active": True, "password_hash": password_hash,
                            "created_at": stamp, "updated_at": stamp}
                    self.database.users.insert_one(user, session=session)
                query = {"course_id": course["_id"], "user_id": user["_id"]}
                existing = self.database.enrollments.find_one(query, session=session)
                payment = "paid" if existing and existing["payment_status"] == "paid" else attendee["paymentStatus"]
                self.database.enrollments.update_one(query, {"$set": {"enrollment_source": attendee["enrollmentSource"], "payment_status": payment},
                    "$setOnInsert": {"_id": new_id(), "schema_version": 1, "enrolled_at": now()}}, upsert=True, session=session)
                result.append({"userId": user["_id"], "name": user["name"], "email": user["email"],
                               "enrollmentSource": attendee["enrollmentSource"], "paymentStatus": payment})
            return {"courseSlug": course_slug, "attendees": result}
        return self._transaction(add)
