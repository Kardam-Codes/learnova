"""Private consistent logical backup and content fingerprints before service conversion."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from bson import BSON
from pymongo import MongoClient
import yaml

ROOT = Path(__file__).resolve().parents[3]
CONFIG = Path(r"C:\Program Files\MongoDB\Server\8.3\bin\mongod.cfg")
TOOLS = ROOT / ".local/tools/mongodb-database-tools-windows-x86_64-100.19.1/bin"


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def inventory(client):
    result = {}
    for name in sorted(set(client.list_database_names()) - {"admin", "config", "local"}):
        collections = {}
        for item in client[name].list_collections():
            if item.get("type") == "view" or item["name"].startswith("system."):
                continue
            checksum = hashlib.sha256()
            count = 0
            for document in client[name][item["name"]].find().sort("_id", 1):
                checksum.update(BSON.encode(document))
                count += 1
            collections[item["name"]] = {"count": count, "sha256": checksum.hexdigest()}
        result[name] = collections
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    with MongoClient("mongodb://localhost:27017/?directConnection=true", serverSelectionTimeoutMS=5000) as client:
        if args.verify:
            saved = json.loads((args.verify / "manifest.json").read_text())
            actual = inventory(client)
            for database, collections in saved["inventory"].items():
                if actual.get(database) != collections:
                    raise RuntimeError("Existing MongoDB data fingerprints changed; inspect the private manifest.")
            print("All pre-existing MongoDB user-database fingerprints match.")
            return
        run = ROOT / ".local/migration-baseline" / ("mongo-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
        run.mkdir(parents=True, exist_ok=False)
        shutil.copy2(CONFIG, run / "mongod.original.cfg")
        config = yaml.safe_load(CONFIG.read_text())
        if config.get("replication"):
            raise RuntimeError("Replication already configured; review instead of replacing it.")
        if config.get("net", {}).get("bindIp") != "127.0.0.1":
            raise RuntimeError("Unexpected network configuration; review before service changes.")
        text = CONFIG.read_text()
        if "#replication:" not in text:
            raise RuntimeError("Unexpected configuration layout.")
        (run / "mongod.replica-set.cfg").write_text(text.replace("#replication:", "replication:\n  replSetName: learnova-rs"), encoding="utf-8")
        metadata = {"created_at": datetime.now(timezone.utc).isoformat(),
                    "server_version": client.server_info()["version"], "replica_set": "learnova-rs"}
        locked = False
        try:
            client.admin.command({"fsync": 1, "lock": True})
            locked = True
            metadata["inventory"] = inventory(client)
            process = subprocess.run([str(TOOLS / "mongodump.exe"), "--host=localhost", "--port=27017",
                                      "--archive=" + str(run / "mongodb.archive.gz"), "--gzip"],
                                     capture_output=True, text=True, timeout=600)
            (run / "mongodump.log").write_text(process.stdout + process.stderr)
            if process.returncode:
                raise RuntimeError("MongoDB backup failed; inspect the private dump log.")
        finally:
            if locked:
                client.admin.command({"fsyncUnlock": 1})
        metadata["files"] = {name: digest(run / name) for name in
                             ["mongodb.archive.gz", "mongod.original.cfg", "mongod.replica-set.cfg"]}
        (run / "manifest.json").write_text(json.dumps(metadata, indent=2))
        print(json.dumps({"backup": str(run.relative_to(ROOT)), "user_databases": len(metadata["inventory"]),
                          "archive_bytes": (run / "mongodb.archive.gz").stat().st_size}, indent=2))


if __name__ == "__main__":
    main()
