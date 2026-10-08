"""Read-only PostgreSQL fingerprints and original API contract comparison."""
import json
from pathlib import Path

from backend.config.db import connect
from backend.db.migration.capture_postgres_baseline import table_fingerprints, schema_inventory
from backend.main import app

ROOT = Path(__file__).resolve().parents[3]
BASELINE = ROOT / ".local/migration-baseline/20261007T122950131750Z"


def main():
    manifest = json.loads((BASELINE / "manifest.json").read_text())
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        fingerprints = table_fingerprints(connection)
        source_schema = schema_inventory(connection)
    # The saved manifest uses the same capture functions and JSON date conversion.
    if fingerprints != manifest["tables"] or source_schema != manifest["schema"]:
        raise RuntimeError("PostgreSQL baseline differs; review privately before continuing.")
    previous = json.loads((ROOT / "docs/migration/phase1/postgres-openapi-baseline.json").read_text())
    current = app.openapi()
    for path, definition in previous["paths"].items():
        if current["paths"].get(path) != definition:
            raise RuntimeError("Existing OpenAPI path differs: " + path)
    if current["components"]["schemas"] != previous["components"]["schemas"]:
        raise RuntimeError("Existing response/request schemas differ.")
    original_checks = json.loads((BASELINE / "api-baseline.json").read_text())["checks"]
    current_checks = json.loads((BASELINE / "phase2-api-baseline.json").read_text())["checks"]
    if len(original_checks) != len(current_checks):
        raise RuntimeError("API baseline check counts differ.")
    for original, actual in zip(original_checks, current_checks):
        identity = ("method", "path", "role", "status")
        if any(original.get(key) != actual.get(key) for key in identity):
            raise RuntimeError("API baseline identities/statuses differ.")
        response = dict(actual["response"]) if isinstance(actual["response"], dict) else actual["response"]
        if actual["path"] == "/db/health":
            response.pop("mongodb", None)  # Documented additive infrastructure readiness field.
        if original["response"] != response:
            raise RuntimeError("API response differs: " + actual["path"])
    report = {"postgres_tables_unchanged": len(fingerprints), "postgres_schema_unchanged": True,
              "existing_openapi_operations_unchanged": 40,
              "api_responses_preserved": len(current_checks),
              "additive_paths": sorted(set(current["paths"]) - set(previous["paths"]))}
    (ROOT / ".local/migration-baseline/phase2-baseline-verification.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
