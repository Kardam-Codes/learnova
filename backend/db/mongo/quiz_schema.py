"""Explicit additive quiz receipt migration; v1 and historical documents stay intact."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from fastapi import HTTPException

from backend.config.mongo import create_mongo_client, get_mongo_settings
from backend.db.mongo.init_db import (
    MIGRATION_ID, SchemaDriftError, assert_development_database, index_options, load_spec,
)

EXTENSION_ID = "mongodb-quiz-receipts-v2"
EXTENSION_PATH = Path(__file__).resolve().parents[3] / "docs/migration/phase7/mongodb-quiz-receipts-v2.json"


def load_extension():
    raw = EXTENSION_PATH.read_bytes()
    definition = json.loads(raw)
    if definition["migration_id"] != EXTENSION_ID or definition["version"] != 2:
        raise SchemaDriftError("Unexpected quiz receipt migration identity.")
    return definition, hashlib.sha256(raw).hexdigest()


def extended_definitions(spec, base_checksum):
    extension, checksum = load_extension()
    if extension["base_checksum"] != base_checksum:
        raise SchemaDriftError("Quiz receipt migration requires the frozen v1 schema.")
    definitions = deepcopy(spec["collections"])
    properties = definitions["quiz_attempts"]["validator"]["$jsonSchema"]["properties"]
    if set(properties) & set(extension["quiz_attempt_properties"]):
        raise SchemaDriftError("Quiz receipt migration must only add optional fields.")
    properties.update(extension["quiz_attempt_properties"])
    return definitions, checksum


def definitions_for_extensions(spec, base_checksum, records):
    definitions, checksum = extended_definitions(spec, base_checksum)
    if (len(records) != 1 or records[0]["_id"] != EXTENSION_ID or records[0].get("version") != 2
            or records[0].get("checksum") != checksum):
        raise SchemaDriftError("Unknown or changed schema extension; explicit migration review is required.")
    return definitions


def require_quiz_receipts(database, session=None):
    _, checksum = load_extension()
    record = database.schema_migrations.find_one({"_id": EXTENSION_ID}, session=session)
    if not record or record.get("version") != 2 or record.get("checksum") != checksum:
        raise HTTPException(503, "MongoDB quiz receipt schema setup is incomplete. Run the Phase 7 migration first.")


def upgrade_quiz_receipts(database):
    assert_development_database(database.name)
    hello = database.client.admin.command("hello")
    if not hello.get("setName") or not hello.get("isWritablePrimary"):
        raise RuntimeError("Quiz receipt migration requires a writable replica-set primary.")
    spec, base_checksum = load_spec()
    definitions, checksum = extended_definitions(spec, base_checksum)
    records = list(database.schema_migrations.find())
    base = [row for row in records if row["_id"] == MIGRATION_ID]
    extensions = [row for row in records if row["_id"] != MIGRATION_ID]
    if (len(base) != 1 or base[0].get("version") != 1 or base[0].get("checksum") != base_checksum):
        raise SchemaDriftError("Initialize and verify the frozen v1 schema before the Phase 7 migration.")
    if extensions:
        definitions_for_extensions(spec, base_checksum, extensions)
    existing = {row["name"]: row for row in database.list_collections()}
    if set(existing) != set(definitions):
        raise SchemaDriftError("Quiz receipt migration requires exactly the managed v1 collections.")
    # Full read-only preflight before DDL. Resume only our exact additive validator
    # if an interruption occurred after collMod but before recording the ledger.
    quiz_already_extended = False
    for name, desired in definitions.items():
        info = existing[name]
        expected = {key: desired[key] for key in ("validator", "validationLevel", "validationAction")}
        actual = info.get("options", {})
        if name == "quiz_attempts":
            quiz_already_extended = actual == expected
            legacy = {key: spec["collections"][name][key] for key in expected}
            permitted = (expected,) if extensions else (legacy, expected)
        else:
            permitted = (expected,)
        if info.get("type") != "collection" or actual not in permitted:
            raise SchemaDriftError("Collection options differ before quiz receipt migration: " + name)
        expected_indexes = {item["name"]: index_options(item) for item in desired["indexes"]}
        # list_indexes uses SON keys; normalize explicitly rather than interpreting field names as pairs.
        actual_indexes = {item["name"]: index_options({**dict(item), "key": list(item["key"].items())})
                          for item in database[name].list_indexes() if item["name"] != "_id_"}
        if actual_indexes != expected_indexes:
            raise SchemaDriftError("Index definitions differ before quiz receipt migration: " + name)
    if not quiz_already_extended:
        desired = definitions["quiz_attempts"]
        database.command({"collMod": "quiz_attempts", **{key: desired[key]
                         for key in ("validator", "validationLevel", "validationAction")}})
    database.schema_migrations.update_one({"_id": EXTENSION_ID}, {"$setOnInsert": {
        "version": 2, "checksum": checksum, "applied_at": datetime.now(timezone.utc)}}, upsert=True)
    return {"database": database.name, "migration": EXTENSION_ID, "checksum": checksum,
            "base_checksum": base_checksum, "domain_records_rewritten": 0}


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    settings = get_mongo_settings()
    if settings is None:
        raise SystemExit("Configure MongoDB first.")
    with create_mongo_client(settings) as client:
        print(json.dumps(upgrade_quiz_receipts(client[settings.database]), indent=2))


if __name__ == "__main__":
    main()
