"""Restore user databases into guarded disposable namespaces and verify their hashes."""
import argparse
import json
from pathlib import Path
import subprocess
import re
from uuid import uuid4

from pymongo import MongoClient

from backend.db.migration.prepare_mongo_service import ROOT, TOOLS, digest, inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup-directory", required=True, type=Path)
    args = parser.parse_args()
    run = args.backup_directory.resolve()
    if not run.is_relative_to(ROOT / ".local/migration-baseline"):
        parser.error("Use a private workspace backup directory.")
    manifest = json.loads((run / "manifest.json").read_text())
    archive = run / "mongodb.archive.gz"
    if digest(archive) != manifest["files"][archive.name]:
        raise RuntimeError("Archive checksum mismatch.")
    verified = 0
    with MongoClient("mongodb://localhost:27017/?replicaSet=learnova-rs", serverSelectionTimeoutMS=5000) as client:
        for source, expected in manifest["inventory"].items():
            name = "learnova_test_" + uuid4().hex
            assert name not in client.list_database_names() and name not in manifest["inventory"]
            try:
                result = subprocess.run([str(TOOLS / "mongorestore.exe"),
                    "--uri=mongodb://localhost:27017/?replicaSet=learnova-rs",
                    "--archive=" + str(archive), "--gzip", "--stopOnError",
                    "--nsInclude=" + source + ".*", "--nsFrom=" + source + ".*", "--nsTo=" + name + ".*"],
                    capture_output=True, text=True, timeout=120)
                (run / f"restore-{verified + 1}.log").write_text(result.stdout + result.stderr)
                if result.returncode:
                    raise RuntimeError("Restore rehearsal failed; see private restore log.")
                if inventory(client).get(name, {}) != expected:
                    raise RuntimeError("Restored user-database fingerprints differ.")
                verified += 1
            finally:
                assert re.fullmatch(r"learnova_test_[0-9a-f]{32}", name) and name not in manifest["inventory"]
                client.drop_database(name)
    report = {"user_databases_restored_and_verified": verified, "source_writes": False,
              "temporary_databases_removed": True, "archive_sha256": digest(archive)}
    (run / "restore-verification.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
