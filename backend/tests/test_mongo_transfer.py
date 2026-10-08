"""Transfer and recovery guards; these tests have not been executed yet."""
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from backend.db.migration.transfer import (
    ROOT, atomic_json, cell, uncell, chunks, digest, guard_target, private_path, transfer,
)
from backend.db.migration.recovery import backup, restore, fingerprint, rollback_plan
from backend.db.mongo.payment_schema import upgrade_payment_intents
from backend.db.mongo.quiz_schema import upgrade_quiz_receipts
from backend.db.mongo.init_db import load_spec
from backend.db.mongo.seed import fixture_documents, fixture_id, STAMP
from backend.tests.conftest import isolated_database


@pytest.mark.parametrize("value", [None, True, 45, "ordinary $text", uuid4(), Decimal("19.99"),
                                  datetime(2026, 1, 1, tzinfo=timezone.utc), {"kind": "decimal", "value": "text"}])
def test_export_cell_roundtrip(value):
    assert uncell(cell(value)) == value


@pytest.mark.parametrize("value", [float("nan"), Decimal("Infinity"), datetime(2026, 1, 1)])
def test_export_rejects_unsupported_values(value):
    with pytest.raises(ValueError):
        cell(value)


def test_private_artifacts_cannot_escape_project():
    with pytest.raises(ValueError):
        private_path(Path.cwd() / "public-export.json")


def test_checkpoint_refuses_changed_and_deleted_target_documents(database):
    original = database.users.find_one()
    expected = {"users": list(database.users.find())}
    checkpoint = {"inserted": {"users": [original["_id"]]}}
    guard_target(database, expected, checkpoint)
    database.users.update_one({"_id": original["_id"]}, {"$set": {"name": "Changed after transfer"}})
    with pytest.raises(ValueError, match="changed"):
        guard_target(database, expected, checkpoint)
    database.users.delete_one({"_id": original["_id"]})
    with pytest.raises(ValueError, match="disappeared"):
        guard_target(database, expected, checkpoint)


def test_batches_bound_count_and_reject_oversized_documents():
    assert [len(batch) for batch in chunks([{"_id": str(n)} for n in range(5)], 2)] == [2, 2, 1]
    with pytest.raises(ValueError):
        list(chunks([{"_id": "large", "value": "x" * (16 * 1024 * 1024)}], 250))


def test_backup_restore_and_rollback_change_guard(database, mongo_client):
    upgrade_quiz_receipts(database)
    upgrade_payment_intents(database)
    root = private_path(Path.cwd() / ".local/deferred-tests" / uuid4().hex)
    bundle = root / "backup"
    before = fingerprint(database)
    assert backup(database, bundle)["dry_run"]
    assert not bundle.exists()
    backup(database, bundle, apply=True, writes_paused=True)
    # Restore requires a wholly absent DB; isolated_database initializes schema.
    name = "learnova_test_" + uuid4().hex
    target = mongo_client[name]
    try:
        assert restore(target, bundle)["dry_run"]
        assert restore(target, bundle, apply=True, writes_paused=True)["restored_fingerprints_match"]
        assert fingerprint(target) == before
        with pytest.raises(ValueError, match="empty"):
            restore(target, bundle, apply=True, writes_paused=True)
        rollback_plan(database, bundle, root / "rollback.json")
        database.users.update_one({}, {"$set": {"name": "Post-cutover change"}})
        with pytest.raises(ValueError, match="reconcile"):
            rollback_plan(database, bundle, root / "blocked.json")
    finally:
        mongo_client.drop_database(name)


def test_frozen_import_dry_run_apply_resume_and_target_change_guard(mongo_client):
    spec, checksum = load_spec()
    folder = private_path(ROOT / ".local/deferred-tests" / uuid4().hex / "export")
    folder.mkdir(parents=True)
    manifest = {"format": 1, "schema_checksum": checksum, "tables": {}, "foreign_keys": [],
                "report": {"columns": [], "rows": []}}
    for table, mapping in spec["source_mapping"].items():
        path = folder / (table + ".jsonl")
        path.write_text("", encoding="utf-8")
        manifest["tables"][table] = {"columns": list(mapping["fields"]), "rows": 0, "sha256": digest(path)}
    atomic_json(folder / "manifest.json", manifest)
    run_id = "deferred-test-" + uuid4().hex
    with isolated_database(mongo_client) as target:
        upgrade_quiz_receipts(target)
        upgrade_payment_intents(target)
        assert transfer(target, folder, run_id, 2)["dry_run"]
        with pytest.raises(ValueError, match="writers"):
            transfer(target, folder, run_id, 2, apply=True)
        first = transfer(target, folder, run_id, 2, apply=True, writes_paused=True)
        assert first["source_tables_preserved"] == 19
        assert first["report"]["filters_compared"] == 4
        assert transfer(target, folder, run_id, 2, apply=True, writes_paused=True) == first
        # Source bundle checksum change must never silently resume a different snapshot.
        manifest["created_at"] = "different export"
        atomic_json(folder / "manifest.json", manifest)
        with pytest.raises(ValueError, match="another source"):
            transfer(target, folder, run_id, 2, apply=True, writes_paused=True)


def nonempty_export_fixture():
    """Private synthetic SQL-shaped rows, including paid access without an order."""
    spec, checksum = load_spec()
    fixture = fixture_documents()
    source = {table: [] for table in spec["source_mapping"]}
    for table in ("users", "courses", "course_tags", "course_content"):
        mapping = spec["source_mapping"][table]
        for document in fixture[mapping["collection"]]:
            row = {key: document.get("_id" if key == "id" else key) for key in mapping["fields"]}
            if table == "courses":
                row["price"] = Decimal(document["price_paise"]) / 100
                for link in document["tags"]:
                    source["course_tag_map"].append({"id": link["id"], "course_id": document["_id"],
                                                     "tag_id": link["tag_id"]})
            source[table].append(row)
    source["course_attendees"] = [{"id": str(uuid4()), "course_id": fixture_id("course-payment"),
        "user_id": fixture_id("learner"), "enrolled_at": STAMP,
        "enrollment_source": "invited", "payment_status": "paid"}]
    folder = private_path(ROOT / ".local/deferred-tests" / uuid4().hex / "export")
    folder.mkdir(parents=True)
    report = {"course_id": fixture_id("course-payment"), "course_name": "Demo payment",
        "participant_id": fixture_id("learner"), "participant_name": "Demo learner",
        "enrolled_date": STAMP, "start_date": None, "completed_date": None,
        "completion_percentage": None, "status": None, "time_spent": 0}
    manifest = {"format": 1, "schema_checksum": checksum, "foreign_keys": [], "tables": {},
                "report": {"columns": list(report), "rows": [[cell(item) for item in report.values()]]}}
    for table, mapping in spec["source_mapping"].items():
        columns = list(mapping["fields"])
        path = folder / (table + ".jsonl")
        import json
        path.write_text("".join(json.dumps([cell(row[key]) for key in columns]) + "\n"
                                for row in source[table]), encoding="utf-8")
        manifest["tables"][table] = {"columns": columns, "rows": len(source[table]), "sha256": digest(path)}
    atomic_json(folder / "manifest.json", manifest)
    return folder


def test_nonempty_import_resumes_commit_before_checkpoint_and_preserves_paid_access(mongo_client, monkeypatch):
    from backend.db.migration import transfer as module
    folder = nonempty_export_fixture()
    run_id = "deferred-crash-" + uuid4().hex
    with isolated_database(mongo_client) as target:
        upgrade_quiz_receipts(target)
        upgrade_payment_intents(target)
        real_write = module.atomic_json
        def fail_after_commit(path, value):
            if value.get("inserted", {}).get("users"):
                raise RuntimeError("Synthetic checkpoint interruption")
            return real_write(path, value)
        with monkeypatch.context() as patch:
            patch.setattr(module, "atomic_json", fail_after_commit)
            with pytest.raises(RuntimeError, match="interruption"):
                transfer(target, folder, run_id, 2, apply=True, writes_paused=True)
        assert target.users.count_documents({}) == 2
        result = transfer(target, folder, run_id, 2, apply=True, writes_paused=True)
        assert result["domain_totals"]["access_status_counts"] == {"paid": 1}
        assert target.payment_orders.count_documents({}) == 0
        assert transfer(target, folder, run_id, 2, apply=True, writes_paused=True) == result
        target.courses.update_one({}, {"$set": {"title": "New MongoDB write"}})
        with pytest.raises(ValueError, match="changed"):
            transfer(target, folder, run_id, 2, apply=True, writes_paused=True)
