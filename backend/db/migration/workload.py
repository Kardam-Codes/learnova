"""Opt-in staging volume generator and read-only query measurement.

Seed uses a frozen source bundle, rewrites every identity, disables copied users,
and replaces password hashes and gateway IDs. It never contacts a payment provider.
"""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import statistics
from time import perf_counter
from uuid import NAMESPACE_URL, UUID, uuid5

from pymongo import MongoClient
from fastapi import HTTPException

from backend.db.migration.transfer import (
    ORDER, chunks, guard_target, import_lock, load_snapshot, prepared_documents,
    private_path, validate_documents,
)
from backend.db.mongo.bootstrap import initialize_auth_bootstrap
from backend.db.mongo.transactions import run_transaction
from backend.modules.admin.mongo_reporting import course_progress_report, report_pipeline
from backend.modules.courses.mongo_service import MongoCourseService


def volume_documents(source, copies):
    combined = {table: [] for table in source}
    for copy in range(copies):
        identities = {row["id"]: uuid5(NAMESPACE_URL, f"learnova-volume:{copy}:{row['id']}")
                      for rows in source.values() for row in rows}
        def rewrite(value):
            if isinstance(value, UUID):
                return identities.get(value, value)
            if isinstance(value, dict):
                return {key: rewrite(item) for key, item in value.items()}
            if isinstance(value, list):
                return [rewrite(item) for item in value]
            return value
        for table, rows in source.items():
            for original in rows:
                row = rewrite(deepcopy(original))
                token = row["id"].hex
                if table == "users":
                    row.update(name=f"Volume Learner {token[:12]}", email=f"volume-{token}@example.invalid",
                               is_active=False)
                    if row["password_hash"] is not None:
                        row["password_hash"] = "!disabled-volume-fixture"
                    if row["google_id"] is not None:
                        row["google_id"] = "volume" + token
                if table in {"courses", "course_content"}:
                    row["slug"] = "volume-" + token
                    row["title"] = f"Volume {table} {token[:12]}"
                if table == "course_tags":
                    row["name"] = "Volume Tag " + token
                if table == "course_payment_orders":
                    row["provider_order_id"] = "order_volume" + token
                    if row["provider_payment_id"] is not None:
                        row["provider_payment_id"] = "pay_volume" + token
                    if row["receipt"] is not None:
                        row["receipt"] = "vol" + token
                combined[table].append(row)
    return prepared_documents(combined)


def seed(database, snapshot, copies, apply, writes_paused):
    with import_lock(database):
        return _seed_locked(database, snapshot, copies, apply, writes_paused)


def _seed_locked(database, snapshot, copies, apply, writes_paused):
    if not re.fullmatch(r"learnova_test_[0-9a-f]{32}", database.name):
        raise ValueError("Volume seeds require a separate unique Learnova test database.")
    if apply and not writes_paused:
        raise ValueError("Stop staging writers before applying a volume seed.")
    source, _ = load_snapshot(snapshot)
    documents = volume_documents(source, copies)
    validate_documents(database, documents, 250)
    guard_target(database, documents, None)
    if apply:
        for name in ORDER:
            for batch in chunks(documents[name], 250):
                run_transaction(database, lambda session: database[name].insert_many(batch, session=session))
        initialize_auth_bootstrap(database)
    return {"dry_run": not apply, "copies": copies,
            "documents": {name: len(rows) for name, rows in documents.items()}}


def measure(database, repetitions, include_writes=False):
    service = MongoCourseService(database)
    enrollment = None
    for candidate in database.enrollments.find({"payment_status": {"$in": ["paid", "not_required"]}}):
        if database.courses.find_one({"_id": candidate["course_id"], "is_published": True}):
            enrollment = candidate
            break
    if enrollment is None:
        raise ValueError("Measurement needs an authorized enrollment fixture.")
    stored_user = database.users.find_one({"_id": enrollment["user_id"]})
    course = database.courses.find_one({"_id": enrollment["course_id"], "is_published": True})
    if stored_user is None or course is None:
        raise ValueError("Choose a staging dataset with a published enrolled course.")
    user = {**stored_user, "id": stored_user["_id"]}
    operations = {
        "catalog": lambda: service.list_courses_for_user(user),
        "course_detail": lambda: service.get_course_detail_for_user(course["slug"], user),
        "report": lambda: course_progress_report(database),
    }
    content = database.course_content.find_one({"course_id": course["_id"], "content_type": "quiz"})
    if content:
        operations["quiz_load"] = lambda: service.get_quiz_for_user(course["slug"], content["slug"], user)
    if include_writes:
        if (not re.fullmatch(r"learnova_test_[0-9a-f]{32}", database.name)
                or not stored_user["email"].endswith("@example.invalid")
                or not stored_user["email"].startswith("volume-") or stored_user["is_active"]):
            raise ValueError("Write measurements require an isolated disabled volume-fixture user.")
        operations["review_write"] = lambda: service.submit_course_review(
            course["slug"], user, 4, "Synthetic performance measurement")
    timings = {}
    for name, callback in operations.items():
        values = []
        for _ in range(repetitions):
            start = perf_counter()
            try:
                callback()
            except HTTPException as error:
                if name != "quiz_load" or error.status_code not in {403, 404, 409}:
                    raise
                timings[name] = {"not_measured": "Fixture quiz access gate", "status": error.status_code}
                break
            values.append((perf_counter() - start) * 1000)
        if values:
            timings[name] = {"samples_ms": values, "median_ms": statistics.median(values), "max_ms": max(values)}
    plan = database.command({"explain": {"aggregate": "enrollments",
        "pipeline": report_pipeline(), "cursor": {}}, "verbosity": "executionStats"})
    return {"database": database.name, "timings": timings, "report_explain": plan,
            "write_measurement": "Synthetic review writes enabled." if include_writes else "Read-only; enable --include-writes on a separate volume fixture to measure review writes.",
            "index_decision": "Review execution statistics before adding indexes or changing pagination."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-uri-env", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--output", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    generator = commands.add_parser("seed")
    generator.add_argument("--snapshot", required=True, type=Path)
    generator.add_argument("--copies", type=int, default=10)
    generator.add_argument("--apply", action="store_true")
    generator.add_argument("--confirm-writes-paused", action="store_true")
    benchmark = commands.add_parser("measure")
    benchmark.add_argument("--repetitions", type=int, default=10)
    benchmark.add_argument("--include-writes", action="store_true")
    args = parser.parse_args()
    if args.command == "seed" and not 1 <= args.copies <= 1000:
        parser.error("Copies must be between 1 and 1000.")
    if args.command == "measure" and not 1 <= args.repetitions <= 100:
        parser.error("Repetitions must be between 1 and 100.")
    output = private_path(args.output)
    if output.exists():
        parser.error("Output already exists; choose a new private artifact path.")
    try:
        with MongoClient(os.environ[args.target_uri_env], tz_aware=True, serverSelectionTimeoutMS=5000) as client:
            database = client[args.database]
            result = seed(database, args.snapshot, args.copies, args.apply, args.confirm_writes_paused) \
                if args.command == "seed" else measure(database, args.repetitions, args.include_writes)
        output.parent.mkdir(parents=True, exist_ok=True)
        # Explain may include BSON metadata. Keep its output private.
        from bson import json_util
        output.write_text(json_util.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps({"artifact": str(output), "command": args.command}))
    except Exception:
        raise SystemExit("Workload command stopped; no provider or cutover operation was performed.") from None


if __name__ == "__main__":
    main()
