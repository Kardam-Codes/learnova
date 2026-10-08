"""Explicit additive checkout recovery schema; no payment/provider calls or data rewrite."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from fastapi import HTTPException
from backend.config.mongo import create_mongo_client, get_mongo_settings
from backend.db.mongo.init_db import MIGRATION_ID, SchemaDriftError, assert_development_database, assert_setup_database, index_options, load_spec

EXTENSION_ID = "mongodb-payment-intents-v3"
EXTENSION_PATH = Path(__file__).resolve().parent / "specs/mongodb-payment-intents-v3.json"


def load_extension():
    raw = EXTENSION_PATH.read_bytes()
    extension = json.loads(raw)
    if extension["migration_id"] != EXTENSION_ID or extension["version"] != 3:
        raise SchemaDriftError("Unexpected payment intent migration identity.")
    return extension, hashlib.sha256(raw).hexdigest()


def extend_definitions(definitions, base_checksum, records):
    extension, checksum = load_extension()
    if (extension["base_checksum"] != base_checksum or len(records) != 1
            or records[0]["_id"] != EXTENSION_ID or records[0].get("version") != 3
            or records[0].get("checksum") != checksum):
        raise SchemaDriftError("Unknown or changed payment schema extension.")
    result = deepcopy(definitions)
    name = extension["collection_name"]
    if name in result:
        raise SchemaDriftError("Payment migration must only add its recovery collection.")
    result[name] = extension["collection"]
    return result


def require_payment_intents(database, session=None):
    _, checksum = load_extension()
    row = database.schema_migrations.find_one({"_id": EXTENSION_ID}, session=session)
    if not row or row.get("version") != 3 or row.get("checksum") != checksum:
        raise HTTPException(503, "MongoDB payment schema setup is incomplete. Run the Phase 8 migration first.")


def upgrade_payment_intents(database, *, application=False):
    from backend.db.mongo.quiz_schema import EXTENSION_ID as QUIZ_ID, definitions_for_extensions, require_quiz_receipts
    assert_setup_database(database.name, application)
    hello = database.client.admin.command("hello")
    if not hello.get("setName") or not hello.get("isWritablePrimary"):
        raise RuntimeError("Payment schema migration requires a writable replica-set primary.")
    spec, base_checksum = load_spec()
    extension, checksum = load_extension()
    if extension["base_checksum"] != base_checksum:
        raise SchemaDriftError("Payment schema requires the frozen v1 definition.")
    records = list(database.schema_migrations.find())
    base = [row for row in records if row["_id"] == MIGRATION_ID]
    if len(base) != 1 or base[0].get("version") != 1 or base[0].get("checksum") != base_checksum:
        raise SchemaDriftError("Initialize the frozen v1 schema first.")
    require_quiz_receipts(database)
    others = [row for row in records if row["_id"] not in {MIGRATION_ID, EXTENSION_ID}]
    definitions = definitions_for_extensions(spec, base_checksum, others)
    if {row["_id"] for row in others} != {QUIZ_ID}:
        raise SchemaDriftError("Payment schema requires exactly the reviewed quiz extension.")
    payment_records = [row for row in records if row["_id"] == EXTENSION_ID]
    desired = extend_definitions(definitions, base_checksum, payment_records or [
        {"_id": EXTENSION_ID, "version": 3, "checksum": checksum}])
    existing = {row["name"]: row for row in database.list_collections()}
    name = extension["collection_name"]
    permitted_sets = (set(desired),) if payment_records else (set(definitions), set(desired))
    if set(existing) not in permitted_sets:
        raise SchemaDriftError("Payment schema has unmanaged or missing collections.")
    for collection, info in existing.items():
        definition = desired[collection]
        expected = {key: definition[key] for key in ("validator", "validationLevel", "validationAction")}
        if info.get("type") != "collection" or info.get("options", {}) != expected:
            raise SchemaDriftError("Collection options differ before payment migration: " + collection)
        expected_indexes = {item["name"]: index_options(item) for item in definition["indexes"]}
        actual = {item["name"]: index_options({**dict(item), "key": list(item["key"].items())})
                  for item in database[collection].list_indexes() if item["name"] != "_id_"}
        # An interruption can leave our new collection with only some reviewed indexes.
        if collection == name and not payment_records:
            valid = all(key in expected_indexes and value == expected_indexes[key] for key, value in actual.items())
        else:
            valid = actual == expected_indexes
        if not valid:
            raise SchemaDriftError("Indexes differ before payment migration: " + collection)
    definition = desired[name]
    if name not in existing:
        database.create_collection(name, **{key: definition[key] for key in ("validator", "validationLevel", "validationAction")})
    for index in definition["indexes"]:
        database[name].create_index([tuple(pair) for pair in index["keys"]], **{key: value for key, value in index.items() if key != "keys"})
    database.schema_migrations.update_one({"_id": EXTENSION_ID}, {"$setOnInsert": {
        "version": 3, "checksum": checksum, "applied_at": datetime.now(timezone.utc)}}, upsert=True)
    return {"database": database.name, "migration": EXTENSION_ID, "checksum": checksum,
            "base_checksum": base_checksum, "collections": 17, "named_indexes": 30, "domain_records_rewritten": 0}


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    settings = get_mongo_settings()
    if settings is None:
        raise SystemExit("Configure MongoDB first.")
    with create_mongo_client(settings) as client:
        print(json.dumps(upgrade_payment_intents(client[settings.database]), indent=2))


if __name__ == "__main__":
    main()
