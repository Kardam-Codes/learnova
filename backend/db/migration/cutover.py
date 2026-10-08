"""Explicit Learnova activation after preserved-data import and acceptance checks.

Commands default to a plan. No database is dropped and PostgreSQL is retained.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re

from pymongo import MongoClient
from backend.db.migration.transfer import (
    ROOT, atomic_json, digest, prepare_target, private_path, transfer,
)
from backend.db.migration.recovery import fingerprint, reviewed_definitions


def update_environment(updates, backup_folder):
    """Preserve all unrelated local configuration; retain the original privately."""
    path = ROOT / ".env"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    backup_folder = private_path(backup_folder)
    backup_folder.mkdir(parents=True, exist_ok=False)
    (backup_folder / "previous.env").write_text(text, encoding="utf-8")
    pending = dict(updates)
    lines = []
    for line in text.splitlines():
        match = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
        key = match.group(1) if match else None
        if key in updates:
            if key in pending:
                lines.append(key + "=" + pending.pop(key))
        else:
            lines.append(line)
    lines.extend(key + "=" + value for key, value in pending.items())
    temporary = path.with_name(".env.cutover.tmp")
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def activate(database, report_path, apply=False, *, uri=None):
    if database.name != "learnova":
        raise ValueError("The approved application database is learnova.")
    report_path = private_path(report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    required = ("backend_tests", "frontend_tests", "frontend_build", "source_preservation",
                "rehearsal_restore", "postgres_restore", "runtime_without_postgres")
    if report.get("accepted") is not True or not all(report.get("checks", {}).get(key) is True for key in required):
        raise ValueError("Acceptance evidence is incomplete.")
    if report.get("database") != database.name or report.get("fingerprints") != fingerprint(database):
        raise ValueError("Application data changed after acceptance evidence.")
    reviewed_definitions(database)
    snapshot = private_path(report["snapshot"])
    if digest(snapshot / "manifest.json") != report["source_sha256"]:
        raise ValueError("Frozen source differs from acceptance evidence.")
    backup = private_path(report["backup"])
    from backend.db.migration.recovery import read_backup
    if read_backup(backup)["fingerprints"] != report["fingerprints"]:
        raise ValueError("The final recovery backup differs from accepted data.")
    if not apply:
        return {"dry_run": True, "database": database.name, "writes_paused": True}
    if not uri or any(char in uri for char in "\r\n"):
        raise ValueError("Activation requires the explicitly verified MongoDB URI.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    update_environment({"AUTH_STORAGE": "mongo", "ADMIN_STORAGE": "mongo", "COURSES_STORAGE": "mongo",
                        "MONGODB_DB": "learnova", "MONGODB_URI": uri, "APPLICATION_WRITES_PAUSED": "true",
                        "VITE_DEMO_MODE": "false"}, ROOT / ".local/migration-runs" / ("activation-" + stamp))
    return {"dry_run": False, "database": database.name, "restart_required": True, "writes_paused": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "import", "activate"))
    parser.add_argument("--target-uri-env", required=True)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--acceptance-report", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-writes-paused", action="store_true")
    args = parser.parse_args()
    if args.apply and not args.confirm_writes_paused:
        parser.error("Stop application writers and pass --confirm-writes-paused.")
    if args.command == "import" and (args.snapshot is None or args.run_id is None):
        parser.error("Import requires --snapshot and --run-id.")
    if args.command == "activate" and args.acceptance_report is None:
        parser.error("Activation requires --acceptance-report.")
    try:
        with MongoClient(os.environ[args.target_uri_env], tz_aware=True, serverSelectionTimeoutMS=5000) as client:
            database = client["learnova"]
            if args.command == "prepare":
                result = prepare_target(database, args.apply, args.confirm_writes_paused, application=True)
            elif args.command == "import":
                result = transfer(database, args.snapshot, args.run_id, 250, args.apply,
                                  args.confirm_writes_paused, application=True)
            else:
                result = activate(database, args.acceptance_report, args.apply, uri=os.environ[args.target_uri_env])
        print(json.dumps(result, indent=2))
    except Exception:
        raise SystemExit("Cutover stopped. Keep writes paused; the original PostgreSQL data has not been deleted.") from None


if __name__ == "__main__":
    main()
