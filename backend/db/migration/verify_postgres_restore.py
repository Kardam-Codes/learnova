"""
File: verify_postgres_restore.py
Owner: BOTH CAN ADD
Purpose: Prove a baseline backup restores into a new isolated PostgreSQL database.
What it is: A guarded restore verification tool that never overwrites a database.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

from backend.config.db import get_database_url
from backend.db.migration.capture_postgres_baseline import (
    file_digest, pg_environment, resolve_tool, schema_inventory, table_fingerprints,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-directory", required=True, type=Path)
    parser.add_argument("--postgres-bin", type=Path)
    args = parser.parse_args()
    run = args.run_directory.resolve()
    if not run.is_relative_to((ROOT / ".local" / "migration-baseline").resolve()):
        parser.error("Use a private baseline run directory in this workspace.")
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["artifacts"].items():
        path = (run / name).resolve()
        if not path.is_relative_to(run) or file_digest(path) != expected["sha256"]:
            parser.error("A backup artifact failed its checksum check.")
    source_url = get_database_url()
    environment, connection_args = pg_environment(source_url)
    database = "learnova_restore_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_") + secrets.token_hex(4)
    if database == manifest["database"] or not database.startswith("learnova_restore_"):
        parser.error("Unsafe restore database name.")
    pg_restore = resolve_tool("pg_restore", args.postgres_bin)
    # This tool only creates a unique new database; it has no drop/clean path.
    with psycopg.connect(make_conninfo(source_url, dbname="postgres"), autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(database)))
    result = {"database": database, "status": "created_restore_pending"}
    output = run / "restore-verification.json"
    try:
        subprocess.run([pg_restore, *connection_args, "--dbname", database,
                        "--no-owner", "--no-acl", "--exit-on-error", str(run / "database.dump")],
                       env=environment, check=True, capture_output=True)
        target_url = make_conninfo(source_url, dbname=database)
        with psycopg.connect(target_url) as restored:
            restored.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            actual_tables = table_fingerprints(restored)
            actual_schema = schema_inventory(restored)
        table_mismatches = sorted(name for name in set(actual_tables) | set(manifest["tables"])
                                  if actual_tables.get(name) != manifest["tables"].get(name))
        # Normalize Decimal enum sort-order values exactly as manifest JSON serialization does.
        actual_schema = json.loads(json.dumps(actual_schema, default=str))
        schema_mismatches = sorted(name for name in set(actual_schema) | set(manifest["schema"])
                                   if actual_schema.get(name) != manifest["schema"].get(name))
        result.update({"table_mismatches": table_mismatches, "schema_mismatches": schema_mismatches,
                       "table_count": len(actual_tables), "status": "restored_and_verified"
                       if not table_mismatches and not schema_mismatches else "verification_failed"})
        if result["status"] != "restored_and_verified":
            raise RuntimeError("Restore contents differ from the captured source snapshot.")
        # Credentials stay in the subprocess environment, not in the saved report/arguments.
        child_environment = dict(os.environ)
        child_environment["DATABASE_URL"] = target_url
        child_environment["DB_NAME"] = database
        checks = subprocess.run([sys.executable, str(Path(__file__).with_name("capture_api_baseline.py")),
                                 "--run-directory", str(run),
                                 "--fixture-name", "restored-api-baseline.json"],
                                env=child_environment, check=True, capture_output=True, text=True)
        result["api_verification_stdout"] = checks.stdout.strip()
        result["status"] = "restored_data_schema_and_read_api_verified"
    except Exception as exc:
        result["failure_type"] = type(exc).__name__
        raise
    finally:
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
