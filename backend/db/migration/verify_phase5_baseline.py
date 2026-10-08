"""Read-only source comparison of MongoDB learner/admin APIs in a disposable target."""
import asyncio
from collections import Counter, defaultdict
from copy import deepcopy
import json
import os
from urllib.parse import quote

import httpx

from backend.config.mongo import create_mongo_client, get_mongo_settings
from backend.config.security import create_access_token
from backend.db.migration.capture_api_baseline import capture
from backend.db.migration.rehearsal_data import capture_source_rows, import_temporary_database, verify_preservation
from backend.db.migration.verify_phase3_baseline import ROOT, BASELINE, source_fingerprints
from backend.db.migration.verify_phase4_baseline import compare_checks, verify_contract, capture_authoring_details
from backend.main import app
from backend.tests.conftest import isolated_database


def compare_learner_checks(before, after, source):
    # The SQL endpoint sorts reviews only by created_at. Canonicalize positions ONLY
    # within groups with identical full source timestamps, never all reviews/arrays.
    metadata = {str(row["id"]): (str(row["course_id"]), row["created_at"]) for row in source["course_reviews"]}
    def section(check):
        body = check["response"]
        if not isinstance(body, dict): return None
        if check["path"].endswith("/reviews"): return body if "items" in body else None
        return body.get("reviews")
    def canonical(checks):
        result = deepcopy(checks)
        for check in result:
            reviews = section(check)
            if reviews is None: continue
            groups = defaultdict(list)
            for index, item in enumerate(reviews["items"]):
                if item["id"] in metadata:
                    groups[metadata[item["id"]]].append(index)
            for positions in groups.values():
                ordered = sorted((reviews["items"][index] for index in positions), key=lambda item: item["id"])
                for index, item in zip(positions, ordered): reviews["items"][index] = item
        return result
    normalized = sum(section(old) != section(new) for old, new in zip(before, after))
    result = compare_checks(canonical(before), canonical(after))
    result["responses_with_equal_source_review_timestamp_tie_normalization"] = normalized
    return result


async def capture_learner_details(source, filename):
    slugs = {str(course["id"]): course["slug"] for course in source["courses"]}
    paths = ["/courses"]
    for course in source["courses"]:
        path = "/courses/" + quote(course["slug"], safe="")
        paths += [path, path + "/reviews"]
    for content in source["course_content"]:
        path = "/courses/" + quote(slugs[str(content["course_id"])], safe="")
        slug = quote(content["slug"], safe="")
        paths.append(path + "/content/" + slug)
        if content["content_mode"] == "quiz":
            paths.append(path + "/quizzes/" + slug)
    missing = "phase5-missing-course"
    if missing in slugs.values():
        raise RuntimeError("The missing-course test slug must not exist in the source.")
    paths += [f"/courses/{missing}", f"/courses/{missing}/reviews", f"/courses/{missing}/content/missing",
              f"/courses/{missing}/quizzes/missing"]
    checks = []
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with app.router.lifespan_context(app), httpx.AsyncClient(transport=transport, base_url="http://baseline.test") as client:
        for user in source["users"]:
            token = create_access_token({"sub": str(user["id"]), "email": user["email"], "role": user["role"]})
            for path in paths:
                response = await client.get(path, headers={"Authorization": "Bearer " + token})
                if response.status_code not in {200, 400, 403, 404}:
                    raise RuntimeError("Unexpected learner read status: " + path)
                checks.append({"method": "GET", "path": path, "role": user["role"],
                               "subject_id": str(user["id"]), "status": response.status_code, "response": response.json()})
    (BASELINE / filename).write_text(json.dumps({"checks": checks}, indent=2) + "\n", encoding="utf-8")
    return checks


def main(phase="phase5", exercise=None, prepare=None):
    if phase not in {"phase5", "phase6", "phase7"}:
        raise ValueError("Unsupported verification phase.")
    settings = get_mongo_settings()
    if settings is None:
        raise RuntimeError("Configure MongoDB before rehearsing learner storage.")
    original = json.loads((BASELINE / "manifest.json").read_text())
    before = source_fingerprints()
    if before != (original["tables"], original["schema"]):
        raise RuntimeError("PostgreSQL differs from the original baseline; inspect privately.")
    source = capture_source_rows()
    original_checks = json.loads((BASELINE / "api-baseline.json").read_text())["checks"]
    saved = {key: os.environ.get(key) for key in ("AUTH_STORAGE", "ADMIN_STORAGE", "COURSES_STORAGE", "MONGODB_DB")}
    ties = Counter((str(row["course_id"]), row["created_at"]) for row in source["course_reviews"])
    report = {**verify_contract(), "persistent_target_imported": False, "source_identities_exercised": len(source["users"]),
              "source_review_timestamp_tie_groups": sum(count > 1 for count in ties.values())}
    try:
        os.environ.update(AUTH_STORAGE="postgres", ADMIN_STORAGE="postgres", COURSES_STORAGE="postgres")
        asyncio.run(capture(BASELINE, f"{phase}-postgres-api-baseline.json"))
        current = json.loads((BASELINE / f"{phase}-postgres-api-baseline.json").read_text())["checks"]
        report["postgres_baseline"] = compare_learner_checks(original_checks, current, source)
        admin = asyncio.run(capture_authoring_details(source, f"{phase}-postgres-authoring-details.json"))
        learner = asyncio.run(capture_learner_details(source, f"{phase}-postgres-learner-details.json"))
        with create_mongo_client(settings) as client, isolated_database(client) as database:
            report.update(import_temporary_database(database, source))
            if prepare is not None:
                report["schema_extension"] = prepare(database)
            os.environ.update(AUTH_STORAGE="mongo", ADMIN_STORAGE="mongo", COURSES_STORAGE="mongo", MONGODB_DB=database.name)
            asyncio.run(capture(BASELINE, f"{phase}-mongo-api-baseline.json"))
            current = json.loads((BASELINE / f"{phase}-mongo-api-baseline.json").read_text())["checks"]
            report["mongo_baseline"] = compare_learner_checks(original_checks, current, source)
            report["authoring_details"] = compare_checks(admin, asyncio.run(
                capture_authoring_details(source, f"{phase}-mongo-authoring-details.json")))
            current = asyncio.run(capture_learner_details(source, f"{phase}-mongo-learner-details.json"))
            # Include each real subject identity in addition to path/role/status/body.
            if [row["subject_id"] for row in learner] != [row["subject_id"] for row in current]:
                raise RuntimeError("Learner subject ordering differs.")
            report["learner_details"] = compare_learner_checks(learner, current, source)
            verify_preservation(database, source)
            report["imported_domain_records_unchanged_after_reads"] = True
            if exercise is not None:
                report["mongo_write_rehearsal"] = exercise(database, source)
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    if source_fingerprints() != before:
        raise RuntimeError("PostgreSQL changed during the learner rehearsal.")
    report.update(postgres_tables_unchanged=len(before[0]), postgres_schema_unchanged=True, temporary_database_removed=True)
    (ROOT / f".local/migration-baseline/{phase}-baseline-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
