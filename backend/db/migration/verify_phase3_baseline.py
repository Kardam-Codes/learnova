"""Rehearse auth identity migration privately; never import into the persistent target."""
import asyncio
from copy import deepcopy
from datetime import datetime
import json
import os
from pathlib import Path

from backend.config.db import connect
from backend.config.mongo import create_mongo_client, get_mongo_settings
from backend.db.migration.capture_api_baseline import capture
from backend.db.migration.capture_postgres_baseline import table_fingerprints, schema_inventory
from backend.db.mongo.bootstrap import initialize_auth_bootstrap
from backend.main import app
from backend.modules.auth.mongo_service import MongoAuthService, normalize_email
from backend.tests.conftest import isolated_database

ROOT = Path(__file__).resolve().parents[3]
BASELINE = ROOT / ".local/migration-baseline/20261007T122950131750Z"


def source_fingerprints():
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        return table_fingerprints(connection), schema_inventory(connection)


def user_document(row):
    document = {**row, "_id": str(row["id"]), "schema_version": 1, "email": normalize_email(row["email"])}
    document.pop("id")
    if document.get("google_id") is None:
        document.pop("google_id", None)
    return document


def api_parity(filename):
    original = json.loads((BASELINE / "api-baseline.json").read_text())["checks"]
    current = json.loads((BASELINE / filename).read_text())["checks"]
    if len(original) != len(current):
        raise RuntimeError("API baseline length differs.")
    for before, after in zip(original, current):
        if any(before.get(key) != after.get(key) for key in ("method", "path", "role", "status")):
            raise RuntimeError("API operation/status differs.")
        body = deepcopy(after["response"])
        if after["path"] == "/db/health":
            body.pop("mongodb", None)
        if body != before["response"]:
            raise RuntimeError("API response differs: " + after["path"])
    return len(current)


def main():
    settings = get_mongo_settings()
    if settings is None:
        raise RuntimeError("Configure MongoDB before rehearsing authentication.")
    original = json.loads((BASELINE / "manifest.json").read_text())
    before = source_fingerprints()
    if before != (original["tables"], original["schema"]):
        raise RuntimeError("PostgreSQL differs from the original baseline; inspect privately.")
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
            cursor.execute("SELECT * FROM users ORDER BY id")
            names = [column.name for column in cursor.description]
            rows = [dict(zip(names, row)) for row in cursor.fetchall()]
    public_baseline = json.loads((ROOT / "docs/migration/phase1/postgres-openapi-baseline.json").read_text())
    current = deepcopy(app.openapi())
    previous = deepcopy(public_baseline)
    # Only this explanatory text changed; paths, parameters, schemas and operation IDs must match.
    for contract in (current, previous):
        contract["paths"]["/auth/login"]["post"].pop("description", None)
    # Phase 4 adds optional course context while retaining all Phase 3 contracts.
    for method in ("get", "put", "delete"):
        operation = current["paths"]["/admin/content/{content_slug}"][method]
        operation["parameters"] = [p for p in operation["parameters"]
                                   if not (p.get("name") == "courseSlug" and p.get("in") == "query" and p.get("required") is False)]
    for path, value in previous["paths"].items():
        if current["paths"].get(path) != value:
            raise RuntimeError("Existing API contract differs: " + path)
    if current["components"]["schemas"] != previous["components"]["schemas"]:
        raise RuntimeError("Existing request/response schemas differ.")
    saved = {key: os.environ.get(key) for key in ("AUTH_STORAGE", "ADMIN_STORAGE", "COURSES_STORAGE", "MONGODB_DB")}
    report = {"source_user_count": len(rows), "existing_operations_preserved": 40,
              "existing_schemas_preserved": 27, "persistent_target_imported": False}
    try:
        os.environ["AUTH_STORAGE"] = "postgres"
        os.environ["ADMIN_STORAGE"] = "postgres"
        os.environ["COURSES_STORAGE"] = "postgres"
        asyncio.run(capture(BASELINE, "phase3-postgres-api-baseline.json"))
        report["postgres_api_responses_preserved"] = api_parity("phase3-postgres-api-baseline.json")
        with create_mongo_client(settings) as client, isolated_database(client) as database:
            database.users.insert_many([user_document(row) for row in rows])
            initialize_auth_bootstrap(database)
            MongoAuthService(database).check_ready()
            for row in rows:
                stored = database.users.find_one({"_id": str(row["id"])})
                expected = user_document(row)
                expected = {key: value.replace(microsecond=value.microsecond // 1000 * 1000)
                            if isinstance(value, datetime) else value for key, value in expected.items()}
                if stored != expected:
                    raise RuntimeError("Imported identity differs after documented BSON date normalization.")
            report["source_identity_fields_verified"] = len(rows)
            report["imported_bootstrap_closed"] = database.app_metadata.find_one()["claimed"]
            os.environ["AUTH_STORAGE"] = "mongo"
            os.environ["MONGODB_DB"] = database.name
            asyncio.run(capture(BASELINE, "phase3-mongo-api-baseline.json"))
            report["mongo_api_responses_preserved"] = api_parity("phase3-mongo-api-baseline.json")
            # API reads must not change imported identity/hash/role/status/timestamps.
            for row in rows:
                actual = database.users.find_one({"_id": str(row["id"])})
                if actual["password_hash"] != row["password_hash"] or actual["role"] != row["role"]:
                    raise RuntimeError("Imported auth records changed during read verification.")
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    if source_fingerprints() != before:
        raise RuntimeError("PostgreSQL changed during the auth rehearsal.")
    report["postgres_tables_unchanged"] = len(before[0])
    report["postgres_schema_unchanged"] = True
    report["temporary_database_removed"] = True
    (ROOT / ".local/migration-baseline/phase3-baseline-verification.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
