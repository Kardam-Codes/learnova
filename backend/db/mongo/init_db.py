"""Explicit, repeatable v1 initialization; schema drift requires a reviewed migration."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from backend.config.mongo import create_mongo_client, get_mongo_settings

SPEC_PATH = Path(__file__).resolve().parents[3] / "docs/migration/phase1/mongodb-schema-v1.json"
MIGRATION_ID = "mongodb-schema-v1"


class SchemaDriftError(RuntimeError):
    pass


def load_spec():
    data = SPEC_PATH.read_bytes()
    return json.loads(data), hashlib.sha256(data).hexdigest()


def assert_development_database(name: str) -> None:
    if name != "learnova_migration_dev" and not re.fullmatch(r"learnova_test_[0-9a-f]{32}", name):
        raise ValueError("Phase 2 setup only permits learnova_migration_dev or a unique Learnova test database.")


def index_options(index):
    result = {"key": [tuple(pair) for pair in index.get("key", index.get("keys", []))],
              "unique": bool(index.get("unique", False))}
    for key in ("partialFilterExpression", "sparse", "expireAfterSeconds", "collation", "hidden"):
        if key in index:
            result[key] = index[key]
    return result


def initialize_database(database) -> dict:
    assert_development_database(database.name)
    hello = database.client.admin.command("hello")
    if not hello.get("setName") or not hello.get("isWritablePrimary"):
        raise RuntimeError("Initialization requires a writable replica-set primary.")
    spec, checksum = load_spec()
    definitions = spec["collections"]
    existing = {item["name"]: item for item in database.list_collections()}
    if set(existing) - set(definitions):
        raise SchemaDriftError("Database contains unmanaged collections; initialization stopped.")
    records = list(database.schema_migrations.find()) if "schema_migrations" in existing else []
    if records:
        base = [record for record in records if record["_id"] == MIGRATION_ID]
        extensions = [record for record in records if record["_id"] != MIGRATION_ID]
        if (len(base) != 1 or base[0].get("version") != spec["spec_version"]
                or base[0].get("checksum") != checksum):
            raise SchemaDriftError("Schema version/checksum differs; a reviewed migration is required.")
        if extensions:
            from backend.db.mongo.quiz_schema import definitions_for_extensions
            definitions = definitions_for_extensions(spec, checksum, extensions)
    if not records and any(database[name].find_one() is not None for name in existing):
        raise SchemaDriftError("Unversioned populated database; refusing to adopt existing records.")
    # Complete preflight before any DDL. Never drop indexes or rewrite validators.
    for name, info in existing.items():
        definition = definitions[name]
        expected = {key: definition[key] for key in ("validator", "validationLevel", "validationAction")}
        options = info.get("options", {})
        if info.get("type") != "collection" or any(options.get(k) != v for k, v in expected.items()):
            raise SchemaDriftError(f"Collection options differ: {name}")
        if set(options) - set(expected):
            raise SchemaDriftError(f"Unexpected collection options: {name}")
        expected_indexes = {idx["name"]: idx for idx in definition["indexes"]}
        for idx in database[name].list_indexes():
            if idx["name"] == "_id_":
                continue
            desired = expected_indexes.get(idx["name"])
            actual = dict(idx)
            actual["key"] = list(idx["key"].items())
            if desired is None or index_options(actual) != index_options(desired):
                raise SchemaDriftError(f"Index definition differs: {name}.{idx['name']}")
    for name, definition in definitions.items():
        if name not in existing:
            database.create_collection(name, **{key: definition[key] for key in
                                               ("validator", "validationLevel", "validationAction")})
        for idx in definition["indexes"]:
            database[name].create_index([tuple(pair) for pair in idx["keys"]],
                                        **{k: v for k, v in idx.items() if k != "keys"})
    database.schema_migrations.update_one({"_id": MIGRATION_ID}, {"$setOnInsert": {
        "version": spec["spec_version"], "checksum": checksum,
        "applied_at": datetime.now(timezone.utc),
    }}, upsert=True)
    return {"database": database.name, "collections": len(definitions),
            "named_indexes": sum(len(d["indexes"]) for d in definitions.values()), "checksum": checksum}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    settings = get_mongo_settings()
    if settings is None:
        raise SystemExit("Set MONGODB_URI and MONGODB_DB first.")
    with create_mongo_client(settings) as client:
        print(json.dumps(initialize_database(client[settings.database]), indent=2))
        from backend.db.mongo.bootstrap import initialize_auth_bootstrap
        initialize_auth_bootstrap(client[settings.database])


if __name__ == "__main__":
    main()
