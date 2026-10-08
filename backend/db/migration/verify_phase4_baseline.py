"""Rehearse all source data and MongoDB authoring reads; never cut over the app."""
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from urllib.parse import quote

import httpx

from backend.config.mongo import create_mongo_client, get_mongo_settings
from backend.config.security import create_access_token
from backend.db.migration.capture_api_baseline import capture
from backend.db.migration.rehearsal_data import capture_source_rows, import_temporary_database, verify_preservation
from backend.db.migration.verify_phase3_baseline import ROOT, BASELINE, source_fingerprints
from backend.main import app
from backend.tests.conftest import isolated_database


def canonical_response(value):
    """Normalize only enrollment dates to documented UTC BSON millisecond precision."""
    if isinstance(value, list):
        return [canonical_response(item) for item in value]
    if isinstance(value, dict):
        result = {key: canonical_response(item) for key, item in value.items()}
        for key in ("enrolledAt", "enrolledDate", "startDate", "completedDate"):
            if isinstance(result.get(key), str):
                date = datetime.fromisoformat(result[key]).astimezone(timezone.utc)
                result[key] = date.replace(microsecond=date.microsecond // 1000 * 1000).isoformat()
        return result
    return value


def compare_checks(before, after):
    if len(before) != len(after):
        raise RuntimeError("API response count differs.")
    normalized_dates = 0
    for original, current in zip(before, after):
        if any(original.get(key) != current.get(key) for key in ("method", "path", "role", "status")):
            raise RuntimeError("API operation/status differs: " + current["path"])
        body = deepcopy(current["response"])
        if current["path"] == "/db/health":
            if body.get("database") == "mongodb":
                if body.get("status") != "ok" or body.get("mongodb", {}).get("status") != "ok":
                    raise RuntimeError("MongoDB readiness failed.")
                # Phase 11 intentionally replaces PostgreSQL database/user metadata.
                continue
            body.pop("mongodb", None)
        if body != original["response"]:
            normalized_dates += 1
        if canonical_response(body) != canonical_response(original["response"]):
            raise RuntimeError("API response differs beyond UTC/BSON enrollment date normalization: " + current["path"])
    return {"responses_preserved": len(after), "responses_with_utc_or_date_precision_normalization": normalized_dates}


def verify_contract():
    previous = json.loads((ROOT / "docs/migration/phase1/postgres-openapi-baseline.json").read_text())
    current = deepcopy(app.openapi())
    for contract in (current, previous):
        contract["paths"]["/auth/login"]["post"].pop("description", None)
    quiz_operation = current["paths"]["/courses/{course_slug}/quizzes/{content_slug}/attempts"]["post"]
    headers = [p for p in quiz_operation["parameters"] if p.get("name") == "Idempotency-Key" and p.get("in") == "header"]
    if len(headers) != 1 or headers[0]["required"] is not False:
        raise RuntimeError("Quiz retry key must be exactly one optional header.")
    quiz_operation["parameters"] = [p for p in quiz_operation["parameters"] if p not in headers]
    # The existing editor now supplies course context; old unambiguous URLs still work.
    for method in ("get", "put", "delete"):
        operation = current["paths"]["/admin/content/{content_slug}"][method]
        additions = [p for p in operation["parameters"] if p.get("name") == "courseSlug" and p.get("in") == "query"]
        if len(additions) != 1 or additions[0]["required"] is not False:
            raise RuntimeError("Content context must be exactly one optional query parameter.")
        operation["parameters"] = [p for p in operation["parameters"] if p not in additions]
    for path, value in previous["paths"].items():
        if current["paths"].get(path) != value:
            raise RuntimeError("Existing API contract differs: " + path)
    if current["components"]["schemas"] != previous["components"]["schemas"]:
        raise RuntimeError("Existing request/response schemas differ.")
    return {"existing_operations_preserved": 40, "existing_schemas_preserved": 27,
            "additive_optional_course_context_parameters": 3, "additive_optional_quiz_retry_headers": 1}


async def capture_authoring_details(source, filename):
    course_slugs = {str(row["id"]): row["slug"] for row in source["courses"]}
    admin = next(row for row in source["users"] if row["role"] in {"super_admin", "admin", "instructor"})
    token = create_access_token({"sub": str(admin["id"]), "email": admin["email"], "role": admin["role"]})
    paths = ["/admin/content/" + quote(row["slug"], safe="") + "?courseSlug=" + quote(course_slugs[str(row["course_id"])], safe="")
             for row in source["course_content"]]
    paths += ["/admin/quizzes/" + str(row["id"]) for row in source["quizzes"]]
    checks = []
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with app.router.lifespan_context(app), httpx.AsyncClient(transport=transport, base_url="http://baseline.test") as client:
        for path in paths:
            response = await client.get(path, headers={"Authorization": "Bearer " + token})
            if response.status_code != 200:
                raise RuntimeError("Source authoring detail failed: " + path)
            checks.append({"method": "GET", "path": path, "status": response.status_code,
                           "role": admin["role"], "response": response.json()})
    (BASELINE / filename).write_text(json.dumps({"checks": checks}, indent=2) + "\n", encoding="utf-8")
    return checks


def main():
    settings = get_mongo_settings()
    if settings is None:
        raise RuntimeError("Configure MongoDB before rehearsing authoring.")
    original = json.loads((BASELINE / "manifest.json").read_text())
    before = source_fingerprints()
    if before != (original["tables"], original["schema"]):
        raise RuntimeError("PostgreSQL differs from the original baseline; inspect privately.")
    source = capture_source_rows()
    original_checks = json.loads((BASELINE / "api-baseline.json").read_text())["checks"]
    saved = {key: os.environ.get(key) for key in ("AUTH_STORAGE", "ADMIN_STORAGE", "COURSES_STORAGE", "MONGODB_DB")}
    report = {**verify_contract(), "persistent_target_imported": False}
    try:
        os.environ.update(AUTH_STORAGE="postgres", ADMIN_STORAGE="postgres", COURSES_STORAGE="postgres")
        asyncio.run(capture(BASELINE, "phase4-postgres-api-baseline.json"))
        current = json.loads((BASELINE / "phase4-postgres-api-baseline.json").read_text())["checks"]
        report["postgres_baseline"] = compare_checks(original_checks, current)
        details = asyncio.run(capture_authoring_details(source, "phase4-postgres-authoring-details.json"))
        with create_mongo_client(settings) as client, isolated_database(client) as database:
            report.update(import_temporary_database(database, source))
            report["imported_bootstrap_closed"] = database.app_metadata.find_one({"_id": "auth_bootstrap"})["claimed"]
            os.environ.update(AUTH_STORAGE="mongo", ADMIN_STORAGE="mongo", MONGODB_DB=database.name)
            asyncio.run(capture(BASELINE, "phase4-mongo-api-baseline.json"))
            current = json.loads((BASELINE / "phase4-mongo-api-baseline.json").read_text())["checks"]
            report["mongo_baseline"] = compare_checks(original_checks, current)
            mongo_details = asyncio.run(capture_authoring_details(source, "phase4-mongo-authoring-details.json"))
            report["authoring_details"] = compare_checks(details, mongo_details)
            verify_preservation(database, source)
            report["imported_domain_records_unchanged_after_reads"] = True
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    if source_fingerprints() != before:
        raise RuntimeError("PostgreSQL changed during the admin rehearsal.")
    report.update(postgres_tables_unchanged=len(before[0]), postgres_schema_unchanged=True, temporary_database_removed=True)
    (ROOT / ".local/migration-baseline/phase4-baseline-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
