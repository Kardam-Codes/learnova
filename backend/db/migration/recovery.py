"""Paused-writer logical backup, separate-target restore, and write-free rollback plan.

Recovery commands default to plans. No command changes application storage selectors.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

from bson import BSON, decode_file_iter
from pymongo import MongoClient

from backend.db.migration.transfer import atomic_json, canonical, digest, private_path
from backend.db.mongo.init_db import load_spec, index_options
from backend.db.mongo.quiz_schema import definitions_for_extensions
from backend.db.mongo.transactions import run_transaction


def fingerprint(database, session=None):
    result = {}
    for name in sorted(database.list_collection_names()):
        checksum, count = hashlib.sha256(), 0
        for row in database[name].find(session=session).sort("_id", 1):
            checksum.update(canonical(row).encode("utf-8"))
            checksum.update(b"\n")
            count += 1
        result[name] = {"rows": count, "sha256": checksum.hexdigest()}
    return result


def reviewed_definitions(database):
    spec, checksum = load_spec()
    records = list(database.schema_migrations.find())
    base = [row for row in records if row["_id"] == "mongodb-schema-v1"]
    if len(base) != 1 or base[0]["checksum"] != checksum:
        raise ValueError("Unknown recovery schema.")
    definitions = definitions_for_extensions(spec, checksum,
        [row for row in records if row["_id"] != "mongodb-schema-v1"])
    existing = {item["name"]: item for item in database.list_collections()}
    if set(existing) != set(definitions):
        raise ValueError("Recovery collection inventory differs from reviewed schema.")
    for name, definition in definitions.items():
        options = {key: definition[key] for key in ("validator", "validationLevel", "validationAction")}
        if existing[name]["options"] != options:
            raise ValueError("Recovery validator differs: " + name)
        actual = {}
        for index in database[name].list_indexes():
            if index["name"] != "_id_":
                actual[index["name"]] = index_options({**index, "key": list(index["key"].items())})
        if actual != {idx["name"]: index_options(idx) for idx in definition["indexes"]}:
            raise ValueError("Recovery indexes differ: " + name)
    return definitions


def backup(database, folder, apply=False, writes_paused=False):
    folder = private_path(folder)
    definitions = reviewed_definitions(database)
    if not apply:
        return {"dry_run": True, "database": database.name, "output": str(folder)}
    if not writes_paused:
        raise ValueError("Pause all application and schema writers before backup.")
    require_primary(database)
    folder.mkdir(parents=True, exist_ok=False)
    def capture(session):
        for name in definitions:
            with (folder / (name + ".bson")).open("wb") as handle:
                for row in database[name].find(session=session).sort("_id", 1):
                    handle.write(BSON.encode(row))
        return fingerprint(database, session)
    fingerprints = run_transaction(database, capture)
    manifest = {"format": 1, "database": database.name, "definitions": definitions,
                "fingerprints": fingerprints,
                "files": {name: digest(folder / (name + ".bson")) for name in definitions}}
    atomic_json(folder / "recovery.json", manifest)
    return {"dry_run": False, "output": str(folder), "collections": len(definitions)}


def read_backup(folder):
    folder = private_path(folder)
    manifest = json.loads((folder / "recovery.json").read_text(encoding="utf-8"))
    if manifest["format"] != 1:
        raise ValueError("Unknown recovery bundle format.")
    # Validate ledger and definitions against local frozen specs before DDL.
    spec, checksum = load_spec()
    with (folder / "schema_migrations.bson").open("rb") as handle:
        records = list(decode_file_iter(handle))
    base = [row for row in records if row["_id"] == "mongodb-schema-v1"]
    if len(base) != 1 or base[0]["checksum"] != checksum:
        raise ValueError("Backup schema checksum differs.")
    definitions = definitions_for_extensions(spec, checksum,
        [row for row in records if row["_id"] != "mongodb-schema-v1"])
    if manifest["definitions"] != definitions or set(manifest["files"]) != set(definitions):
        raise ValueError("Backup definitions differ from reviewed schema.")
    for name, checksum in manifest["files"].items():
        if digest(folder / (name + ".bson")) != checksum:
            raise ValueError("Recovery file checksum differs: " + name)
    return manifest


def restore(database, folder, apply=False, writes_paused=False):
    manifest = read_backup(folder)
    if not re.fullmatch(r"learnova_test_[0-9a-f]{32}", database.name) or database.name == manifest["database"]:
        raise ValueError("Restore requires a separate unique Learnova test database.")
    if database.list_collection_names():
        raise ValueError("Restore destination must be completely empty; no existing data is dropped.")
    if not apply:
        return {"dry_run": True, "source": manifest["database"], "destination": database.name}
    if not writes_paused:
        raise ValueError("Pause target writers before restore.")
    require_primary(database)
    for name, definition in manifest["definitions"].items():
        database.create_collection(name, **{key: definition[key] for key in
                                           ("validator", "validationLevel", "validationAction")})
        for index in definition["indexes"]:
            database[name].create_index([tuple(pair) for pair in index["keys"]],
                **{key: value for key, value in index.items() if key != "keys"})
    from backend.db.migration.transfer import chunks
    for name in manifest["definitions"]:
        with (private_path(folder) / (name + ".bson")).open("rb") as handle:
            for batch in chunks(decode_file_iter(handle), 250):
                run_transaction(database, lambda session: database[name].insert_many(batch, session=session))
    if fingerprint(database) != manifest["fingerprints"]:
        raise ValueError("Restore fingerprint differs; retain the isolated target for investigation.")
    reviewed_definitions(database)
    return {"dry_run": False, "destination": database.name, "restored_fingerprints_match": True}


def require_primary(database):
    hello = database.client.admin.command("hello")
    if not hello.get("setName") or not hello.get("isWritablePrimary"):
        raise ValueError("Recovery writes require a writable replica-set primary.")


def rollback_plan(database, folder, output):
    manifest = read_backup(folder)
    if database.name != manifest["database"]:
        raise ValueError("Rollback reference belongs to another database.")
    if fingerprint(database) != manifest["fingerprints"]:
        raise ValueError("MongoDB changed after the reference backup; reconcile new writes before rollback.")
    output = private_path(output)
    if output.exists():
        raise ValueError("Rollback plan output already exists.")
    output.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(output, {"selectors": {"AUTH_STORAGE": "postgres", "ADMIN_STORAGE": "postgres",
                                      "COURSES_STORAGE": "postgres"},
        "mongo_unchanged_since_reference": True, "application_configuration_changed": False,
        "required_steps": ["Keep writes paused throughout rollback.",
                           "Verify the original PostgreSQL backup and unchanged source.",
                           "Restore the matching application revision and set the listed selectors.",
                           "Restart the backend, verify PostgreSQL flows, then reopen writes."],
        "post_cutover_writes": "Export and reconcile MongoDB changes before any lossless rollback."})
    return {"plan": str(output), "application_configuration_changed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("backup", "restore", "rollback-plan"))
    parser.add_argument("--target-uri-env", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-writes-paused", action="store_true")
    args = parser.parse_args()
    if args.command == "rollback-plan" and (args.output is None or not args.confirm_writes_paused):
        parser.error("Rollback planning requires --output and --confirm-writes-paused.")
    try:
        with MongoClient(os.environ[args.target_uri_env], tz_aware=True, serverSelectionTimeoutMS=5000) as client:
            database = client[args.database]
            if args.command == "rollback-plan":
                result = rollback_plan(database, args.bundle, args.output)
            else:
                callback = backup if args.command == "backup" else restore
                result = callback(database, args.bundle, args.apply, args.confirm_writes_paused)
        print(json.dumps(result, indent=2))
    except Exception:
        raise SystemExit("Recovery operation stopped; no application configuration or original source was changed.") from None


if __name__ == "__main__":
    main()
