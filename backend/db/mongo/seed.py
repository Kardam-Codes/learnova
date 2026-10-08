"""Deterministic, opt-in fixture for empty development/test databases only."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from uuid import NAMESPACE_URL, uuid5

from backend.config.mongo import create_mongo_client, get_mongo_settings
from backend.db.mongo.init_db import assert_development_database, initialize_database

STAMP = datetime(2026, 1, 1, tzinfo=timezone.utc)
DEMO_PASSWORD = "LearnovaDemo!123"


def fixture_id(label):
    return str(uuid5(NAMESPACE_URL, "learnova-phase2:" + label))


def fixture_documents():
    salt = "learnova-phase2-demo-only"
    digest = hashlib.pbkdf2_hmac("sha256", DEMO_PASSWORD.encode(), salt.encode(), 600_000).hex()
    password_hash = f"pbkdf2_sha256$600000${salt}${digest}"
    common = {"schema_version": 1, "created_at": STAMP, "updated_at": STAMP}
    users = [{**common, "_id": fixture_id(role), "name": "Demo " + role,
              "email": role + "@learnova.example", "role": role, "provider": "local",
              "password_hash": password_hash, "is_active": True}
             for role in ("super_admin", "instructor", "learner")]
    tag = {"_id": fixture_id("tag"), "name": "Demo", "normalized_name": "demo",
           "schema_version": 1, "created_at": STAMP}
    courses = [{**common, "_id": fixture_id("course-" + access), "slug": "demo-" + access,
                "title": "Demo " + access, "short_description": "Phase 2 infrastructure fixture",
                "visibility": "everyone", "access_rule": access, "price_paise": price,
                "currency": "INR", "is_published": True, "created_by": fixture_id("instructor"),
                "tags": [{"id": fixture_id("tag-link-" + access), "tag_id": tag["_id"], "name": "Demo"}]}
               for access, price in (("open", 0), ("payment", 9900))]
    content = [{**common, "_id": fixture_id("content-" + mode), "course_id": courses[0]["_id"],
                "slug": "demo-" + mode, "title": "Demo " + mode,
                "content_type": "quiz" if mode == "quiz" else "lesson", "content_mode": mode,
                "allow_download": False, "display_order": order, "attachments": []}
               for order, mode in enumerate(("video", "document", "image", "quiz"), 1)]
    quiz = {**common, "_id": fixture_id("quiz"), "course_id": courses[0]["_id"],
            "content_id": content[3]["_id"], "title": "Demo quiz", "max_attempts": 2, "version": 1,
            "questions": [{"id": fixture_id("question"), "question_text": "Does a transaction roll back?",
                           "display_order": 1, "created_at": STAMP, "updated_at": STAMP,
                           "options": [{"id": fixture_id("option-yes"), "option_text": "Yes",
                                        "is_correct": True, "display_order": 1},
                                       {"id": fixture_id("option-no"), "option_text": "No",
                                        "is_correct": False, "display_order": 2}]}],
            "reward_rules": [{"id": fixture_id("reward"), "attempt_number": 1, "points_awarded": 10}]}
    return {"users": users, "tags": [tag], "courses": courses, "course_content": content,
            "quizzes": [quiz], "app_metadata": [{"_id": "auth_bootstrap", "schema_version": 1,
                "claimed": True, "administrator_id": fixture_id("super_admin"), "updated_at": STAMP}]}


def seed_database(database):
    assert_development_database(database.name)
    initialize_database(database)
    documents = fixture_documents()
    with database.client.start_session() as session:
        with session.start_transaction():
            # Refuse to replace demo or real data. Tests use a new DB each time.
            for name in database.list_collection_names():
                existing = database[name].find_one(session=session)
                if name == "app_metadata" and existing and existing.get("claimed") is False and existing.get("administrator_id") is None:
                    continue  # Explicit schema/auth setup may create an unclaimed empty-target state.
                if name != "schema_migrations" and existing is not None:
                    raise RuntimeError("Seed requires an empty initialized development database.")
            for name, rows in documents.items():
                if name == "app_metadata":
                    database[name].replace_one({"_id": "auth_bootstrap"}, rows[0], upsert=True, session=session)
                else:
                    database[name].insert_many(rows, session=session)
    return {name: len(rows) for name, rows in documents.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", required=True,
                        help="Explicitly create publicly known demo credentials in the empty development database.")
    parser.parse_args()
    settings = get_mongo_settings()
    if settings is None:
        raise SystemExit("Configure MongoDB first.")
    with create_mongo_client(settings) as client:
        print(json.dumps(seed_database(client[settings.database]), indent=2))


if __name__ == "__main__":
    main()
