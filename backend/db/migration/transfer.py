"""Frozen PostgreSQL export and insert-only, resumable MongoDB staging transfer.

No command activates MongoDB. Import defaults to dry-run. Export bundles contain
password hashes and personal records: keep them in the ignored .local directory.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import re
from uuid import UUID, NAMESPACE_URL, uuid5

from bson import BSON, json_util
import psycopg
from psycopg import sql
from pymongo import MongoClient

from backend.db.migration.rehearsal_data import assemble_documents, verify_preservation
from backend.db.mongo.bootstrap import initialize_auth_bootstrap
from backend.db.mongo.init_db import load_spec
from backend.db.mongo.quiz_schema import definitions_for_extensions
from backend.db.mongo.transactions import run_transaction

ROOT = Path(__file__).resolve().parents[3]
ORDER = ("users", "tags", "courses", "course_content", "quizzes", "enrollments",
         "course_progress", "content_progress", "quiz_attempts", "learner_points",
         "point_events", "reviews", "payment_orders", "quiz_attempt_counters")


def private_path(path):
    path = Path(path).resolve()
    if not path.is_relative_to((ROOT / ".local").resolve()):
        raise ValueError("Migration artifacts must stay inside the ignored project .local directory.")
    return path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def cell(value):
    if isinstance(value, UUID):
        return ["uuid", str(value)]
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Nonfinite source decimal.")
        return ["decimal", str(value)]
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("Source timestamps must include a timezone.")
        return ["datetime", value.astimezone(timezone.utc).isoformat()]
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Nonfinite source float.")
    # json serialization rejects unsupported types, including nested nonfinite values.
    json.dumps(value, allow_nan=False)
    return ["json", value]


def uncell(value):
    kind, item = value
    if kind == "uuid":
        return UUID(item)
    if kind == "decimal":
        return Decimal(item)
    if kind == "datetime":
        return datetime.fromisoformat(item)
    if kind != "json":
        raise ValueError("Unknown export cell encoding.")
    return item


def export_snapshot(dsn, folder, batch_size):
    folder = private_path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    spec, checksum = load_spec()
    manifest = {"format": 1, "schema_checksum": checksum, "tables": {},
                "created_at": datetime.now(timezone.utc).isoformat()}
    # One transaction for every table, the FK inventory, and SQL report fixture.
    with psycopg.connect(dsn) as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        connection.execute("SET LOCAL TIME ZONE 'UTC'")
        fk_rows = connection.execute("""
            SELECT child.relname, array_agg(a.attname ORDER BY k.n),
                   parent.relname, array_agg(b.attname ORDER BY k.n)
            FROM pg_constraint c JOIN pg_class child ON child.oid=c.conrelid
            JOIN pg_namespace ns ON ns.oid=child.relnamespace
            JOIN pg_class parent ON parent.oid=c.confrelid
            JOIN LATERAL unnest(c.conkey,c.confkey) WITH ORDINALITY k(x,y,n) ON true
            JOIN pg_attribute a ON a.attrelid=child.oid AND a.attnum=k.x
            JOIN pg_attribute b ON b.attrelid=parent.oid AND b.attnum=k.y
            WHERE c.contype='f' AND ns.nspname='public'
            GROUP BY c.oid,child.relname,parent.relname
        """).fetchall()
        manifest["foreign_keys"] = [list(row) for row in fk_rows]
        for table, mapping in spec["source_mapping"].items():
            count = 0
            with connection.cursor(name="export_" + table) as cursor:
                cursor.execute(sql.SQL("SELECT * FROM public.{} ORDER BY id").format(sql.Identifier(table)))
                # Named cursor description becomes available after the first fetch.
                rows = cursor.fetchmany(batch_size)
                columns = [column.name for column in cursor.description]
                if set(columns) != set(mapping["fields"]):
                    raise RuntimeError("Unmapped source columns: " + table)
                path = folder / (table + ".jsonl")
                with path.open("w", encoding="utf-8", newline="\n") as handle:
                    while rows:
                        for row in rows:
                            handle.write(json.dumps([cell(item) for item in row], allow_nan=False) + "\n")
                            count += 1
                        rows = cursor.fetchmany(batch_size)
                manifest["tables"][table] = {"columns": columns, "rows": count, "sha256": digest(path)}
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM reporting_course_progress ORDER BY course_name, participant_name")
            columns = [column.name for column in cursor.description]
            manifest["report"] = {"columns": columns,
                                  "rows": [[cell(item) for item in row] for row in cursor.fetchall()]}
    atomic_json(folder / "manifest.json", manifest)
    return {"export": str(folder), "tables": len(manifest["tables"]),
            "rows": sum(item["rows"] for item in manifest["tables"].values())}


def load_snapshot(folder):
    folder = private_path(folder)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    spec, checksum = load_spec()
    if manifest["format"] != 1 or manifest["schema_checksum"] != checksum:
        raise ValueError("Unknown or changed source mapping.")
    if set(manifest["tables"]) != set(spec["source_mapping"]):
        raise ValueError("Export table inventory differs from the reviewed mapping.")
    source = {}
    for table, info in manifest["tables"].items():
        path = folder / (table + ".jsonl")
        if digest(path) != info["sha256"]:
            raise ValueError("Export checksum differs: " + table)
        if set(info["columns"]) != set(spec["source_mapping"][table]["fields"]):
            raise ValueError("Export column inventory differs: " + table)
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            values = json.loads(line)
            if len(values) != len(info["columns"]):
                raise ValueError("Export row width differs: " + table)
            rows.append(dict(zip(info["columns"], map(uncell, values))))
        if len(rows) != info["rows"] or len({r["id"] for r in rows}) != len(rows):
            raise ValueError("Export count or duplicate ID differs: " + table)
        source[table] = rows
    for child, columns, parent, parent_columns in manifest["foreign_keys"]:
        if child not in source or parent not in source:
            raise ValueError("Unmapped source foreign-key relationship.")
        parents = {tuple(row[key] for key in parent_columns) for row in source[parent]}
        for row in source[child]:
            key = tuple(row[column] for column in columns)
            if all(value is not None for value in key) and key not in parents:
                raise ValueError("Missing source parent: " + child)
    for row in source["courses"]:
        amount = row["price"] * 100
        if not amount.is_finite() or amount != amount.to_integral_value() or not 0 <= amount <= 9999999999:
            raise ValueError("Price cannot be represented as exact supported paise.")
    return source, manifest


def prepared_documents(source):
    documents = assemble_documents(source)
    counters = {}
    for attempt in documents["quiz_attempts"]:
        pair = (attempt["quiz_id"], attempt["user_id"])
        previous = counters.get(pair)
        if previous is None or attempt["attempt_number"] > previous["attempts_used"]:
            counters[pair] = {"_id": str(uuid5(NAMESPACE_URL, ":".join(pair))),
                "schema_version": 1, "quiz_id": pair[0], "user_id": pair[1],
                "attempts_used": attempt["attempt_number"], "updated_at": attempt["submitted_at"]}
    documents["quiz_attempt_counters"] = list(counters.values())
    return {name: sorted(documents[name], key=lambda row: row["_id"]) for name in ORDER}


def canonical(document):
    # BSON roundtrip normalizes integer widths and the approved millisecond timestamps.
    return json_util.dumps(BSON(BSON.encode(document)).decode(), sort_keys=True,
                           json_options=json_util.CANONICAL_JSON_OPTIONS)


def chunks(rows, size):
    batch, byte_count = [], 0
    for row in rows:
        length = len(BSON.encode(row))
        if length >= 16 * 1024 * 1024:
            raise ValueError("An assembled document reaches the BSON size limit.")
        # Keep read-only validation command below MongoDB's command size limit.
        if batch and (len(batch) >= size or byte_count + length > 8 * 1024 * 1024):
            yield batch
            batch, byte_count = [], 0
        batch.append(row)
        byte_count += length
    if batch:
        yield batch


def validate_documents(database, documents, batch_size):
    from backend.db.migration.recovery import reviewed_definitions
    spec, checksum = load_spec()
    records = list(database.schema_migrations.find())
    base = [row for row in records if row["_id"] == "mongodb-schema-v1"]
    if len(base) != 1 or base[0]["checksum"] != checksum:
        raise ValueError("Prepare the reviewed target schema before transferring.")
    definitions = definitions_for_extensions(spec, checksum,
        [row for row in records if row["_id"] != "mongodb-schema-v1"])
    if not any(row["_id"] == "mongodb-payment-intents-v3" for row in records):
        raise ValueError("Prepare schema versions 1, 2 and 3 before transferring.")
    reviewed_definitions(database)
    for name, rows in documents.items():
        unique = [index for index in definitions[name]["indexes"] if index.get("unique")]
        for index in unique:
            seen = set()
            for row in rows:
                # All reviewed partial unique indexes exclude missing/null IDs.
                key = tuple(row.get(field) for field, _ in index["keys"])
                if index.get("partialFilterExpression") and any(item is None for item in key):
                    continue
                if key in seen:
                    raise ValueError("Duplicate mapped unique key: " + name + "." + index["name"])
                seen.add(key)
        for batch in chunks(rows, batch_size):
            invalid = list(database.aggregate([
                {"$documents": {"$literal": batch}},
                {"$match": {"$nor": [definitions[name]["validator"]]}},
                {"$limit": 1}, {"$project": {"_id": 1}},
            ]))
            if invalid:
                raise ValueError("Mapped document violates schema: " + name)


def target_identity(database):
    return {item["name"]: str(item["info"]["uuid"])
            for item in database.list_collections()}


@contextmanager
def import_lock(database):
    """OS releases this workspace-local target lock even when a process crashes.

    Operators must also exclude writers and import processes on other machines.
    """
    identity = json.dumps(target_identity(database), sort_keys=True).encode()
    key = hashlib.sha256(identity + database.name.encode()).hexdigest()
    path = private_path(ROOT / ".local/migration-runs/locks" / (key + ".lock"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def guard_target(database, documents, checkpoint):
    if database.payment_checkout_intents.find_one() is not None:
        raise ValueError("Checkout activity exists; refusing an import into a live target.")
    acknowledged = checkpoint.get("inserted", {}) if checkpoint else {}
    for name, rows in documents.items():
        expected = {row["_id"]: canonical(row) for row in rows}
        actual = {row["_id"]: canonical(row) for row in database[name].find()}
        if checkpoint is None and actual:
            raise ValueError("A new import requires an empty target: " + name)
        if any(expected.get(key) != value for key, value in actual.items()):
            raise ValueError("Target contains extra or changed records: " + name)
        if not set(acknowledged.get(name, [])) <= set(actual):
            raise ValueError("Previously imported records disappeared: " + name)
    metadata = list(database.app_metadata.find())
    if any(row["_id"] != "auth_bootstrap" for row in metadata):
        raise ValueError("Unknown target application metadata.")
    if checkpoint is None and any(row["claimed"] for row in metadata):
        raise ValueError("A new import requires unclaimed authentication bootstrap.")


def transfer(database, folder, run_id, batch_size, apply=False, writes_paused=False, *, application=False):
    with import_lock(database):
        return _transfer_locked(database, folder, run_id, batch_size, apply, writes_paused, application=application)


def _transfer_locked(database, folder, run_id, batch_size, apply=False, writes_paused=False, *, application=False):
    if not (application and database.name == "learnova") and not re.fullmatch(r"learnova_test_[0-9a-f]{32}", database.name):
        raise ValueError("Phase 10 imports require a separately prepared unique Learnova test database.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", run_id):
        raise ValueError("Invalid run ID.")
    if apply and not writes_paused:
        raise ValueError("Stop target writers and acknowledge --confirm-writes-paused before applying.")
    source, manifest = load_snapshot(folder)
    documents = prepared_documents(source)
    validate_documents(database, documents, batch_size)
    checkpoint_path = private_path(ROOT / ".local/migration-runs" / run_id / "checkpoint.json")
    checkpoint = json.loads(checkpoint_path.read_text()) if checkpoint_path.exists() else None
    identity = {"target": database.name, "collections": target_identity(database),
                "source_sha256": digest(private_path(folder) / "manifest.json")}
    if checkpoint and checkpoint["identity"] != identity:
        raise ValueError("Run ID belongs to another source or target.")
    guard_target(database, documents, checkpoint)
    if not apply:
        return {"dry_run": True, "run_id": run_id,
                "documents": {name: len(rows) for name, rows in documents.items()}}
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = checkpoint or {"identity": identity, "inserted": {}, "complete": False}
    atomic_json(checkpoint_path, checkpoint)
    for name, rows in documents.items():
        for batch in chunks(rows, batch_size):
            def insert(session):
                missing = []
                for row in batch:
                    existing = database[name].find_one({"_id": row["_id"]}, session=session)
                    if existing is None:
                        missing.append(row)
                    elif canonical(existing) != canonical(row):
                        raise ValueError("Target changed during import: " + name)
                if missing:
                    database[name].insert_many(missing, session=session)
            run_transaction(database, insert)
            known = set(checkpoint["inserted"].get(name, []))
            checkpoint["inserted"][name] = sorted(known | {row["_id"] for row in batch})
            # Commit-before-checkpoint crash is safe: exact existing records are reused.
            atomic_json(checkpoint_path, checkpoint)
    guard_target(database, documents, checkpoint)
    result = verify_preservation(database, source)
    result["domain_totals"] = reconcile_totals(database, source)
    result["report"] = reconcile_report(database, manifest)
    initialize_auth_bootstrap(database)
    checkpoint["complete"] = True
    checkpoint["reconciliation"] = result
    atomic_json(checkpoint_path, checkpoint)
    return {"dry_run": False, "run_id": run_id, **result}


def reconcile_report(database, manifest):
    from backend.modules.admin.mongo_reporting import course_progress_report
    records = [dict(zip(manifest["report"]["columns"], map(uncell, row)))
               for row in manifest["report"]["rows"]]
    def stamp(value):
        return value.replace(microsecond=value.microsecond // 1000 * 1000).isoformat() if value else None
    for selected in (None, "yet_to_start", "in_progress", "completed"):
        expected = []
        for row in records:
            if selected and row["status"] != selected:
                continue
            minutes = int(row["time_spent"] or 0)
            expected.append({"courseId": str(row["course_id"]), "courseName": row["course_name"],
                "participantId": str(row["participant_id"]), "participantName": row["participant_name"],
                "enrolledDate": stamp(row["enrolled_date"]), "startDate": stamp(row["start_date"]),
                "completedDate": stamp(row["completed_date"]), "timeSpent": f"{minutes // 60}:{minutes % 60:02d}",
                "completionPercentage": f"{float(row['completion_percentage'] or 0):.0f}%",
                "status": row["status"] or "yet_to_start"})
        actual = course_progress_report(database, selected)
        # SQL does not define ordering between identical course and participant names.
        def ordered(rows):
            return sorted(({key: value for key, value in row.items() if key != "id"} for row in rows),
                          key=lambda row: (row["courseName"], row["participantName"], row["courseId"], row["participantId"]))
        if ordered(actual["rows"]) != ordered(expected):
            raise ValueError("Report rows differ from the frozen SQL view.")
        counts = [len(records), *[sum(row["status"] == state for row in records)
                                for state in ("yet_to_start", "in_progress", "completed")]]
        if [card["value"] for card in actual["summary"]] != counts:
            raise ValueError("Report summary differs from the frozen SQL view.")
    return {"filters_compared": 4, "participants": len(records)}


def verify_migrated_login(database, user_id, password):
    from backend.modules.auth.mongo_service import MongoAuthService
    user = database.users.find_one({"_id": user_id})
    if user is None or user["provider"] != "local" or not user["is_active"]:
        raise ValueError("Select an active migrated local-password user.")
    result = MongoAuthService(database).login_user(email=user["email"], password=password,
                                                 requested_role="admin" if user["role"] == "super_admin" else user["role"])
    # Tokens, email, password and password hashes must never enter an artifact.
    return {"login_verified": bool(result)}


def prepare_target(database, apply=False, writes_paused=False, *, application=False):
    if not (application and database.name == "learnova") and not re.fullmatch(r"learnova_test_[0-9a-f]{32}", database.name):
        raise ValueError("Preparation requires a unique Learnova test database.")
    collections = set(database.list_collection_names())
    for name in collections - {"schema_migrations", "app_metadata"}:
        if database[name].find_one() is not None:
            raise ValueError("Preparation refuses populated staging targets.")
    bootstrap = database.app_metadata.find_one({"_id": "auth_bootstrap"})
    if bootstrap and bootstrap.get("claimed"):
        raise ValueError("Preparation refuses a previously claimed target.")
    if not apply:
        return {"dry_run": True, "database": database.name, "schema_versions": [1, 2, 3]}
    if not writes_paused:
        raise ValueError("Stop target writers before preparing staging schema.")
    from backend.db.mongo.init_db import initialize_database
    from backend.db.mongo.quiz_schema import upgrade_quiz_receipts
    from backend.db.mongo.payment_schema import upgrade_payment_intents
    initialize_database(database, application=application)
    upgrade_quiz_receipts(database, application=application)
    upgrade_payment_intents(database, application=application)
    initialize_auth_bootstrap(database)
    return {"dry_run": False, "database": database.name, "schema_versions": [1, 2, 3]}


def reconcile_totals(database, source):
    """Compare independent balances and event totals; never invent balancing events."""
    from collections import Counter
    def totals(rows, field):
        result = Counter()
        for row in rows:
            result[str(row["user_id"])] += row[field]
        return result
    for table, field in (("learner_points", "total_points"), ("point_events", "points_delta")):
        if totals(source[table], field) != totals(database[table].find(), field):
            raise ValueError("Migrated point totals differ: " + table)
    source_access = Counter(row["payment_status"] for row in source["course_attendees"])
    target_access = Counter(row["payment_status"] for row in database.enrollments.find())
    source_payments = Counter((row["status"], row["currency"]) for row in source["course_payment_orders"])
    target_payments = Counter((row["status"], row["currency"]) for row in database.payment_orders.find())
    if source_access != target_access or source_payments != target_payments:
        raise ValueError("Migrated access or payment totals differ.")
    return {"balances_and_events_compared_separately": True,
            "access_status_counts": dict(target_access), "payment_status_currency_counts_match": True,
            "reviews_compared": len(source["course_reviews"]),
            "quiz_answers_compared": len(source["quiz_attempt_answers"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export")
    export.add_argument("--source-env", required=True, help="Environment variable containing the explicit PostgreSQL DSN")
    export.add_argument("--output", required=True, type=Path)
    export.add_argument("--batch-size", type=int, default=250)
    importer = commands.add_parser("import")
    importer.add_argument("--snapshot", required=True, type=Path)
    importer.add_argument("--target-uri-env", required=True)
    importer.add_argument("--database", required=True)
    importer.add_argument("--run-id", required=True)
    importer.add_argument("--batch-size", type=int, default=250)
    importer.add_argument("--apply", action="store_true")
    importer.add_argument("--confirm-writes-paused", action="store_true")
    login = commands.add_parser("verify-login")
    login.add_argument("--target-uri-env", required=True)
    login.add_argument("--database", required=True)
    login.add_argument("--user-id", required=True)
    login.add_argument("--password-env", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--target-uri-env", required=True)
    prepare.add_argument("--database", required=True)
    prepare.add_argument("--apply", action="store_true")
    prepare.add_argument("--confirm-writes-paused", action="store_true")
    args = parser.parse_args()
    if args.command in {"export", "import"} and not 1 <= args.batch_size <= 1000:
        parser.error("Batch size must be between 1 and 1000.")
    try:
        if args.command == "export":
            result = export_snapshot(os.environ[args.source_env], args.output, args.batch_size)
        else:
            with MongoClient(os.environ[args.target_uri_env], tz_aware=True,
                             serverSelectionTimeoutMS=5000) as client:
                if args.command == "verify-login":
                    result = verify_migrated_login(client[args.database], args.user_id,
                                                  os.environ[args.password_env])
                elif args.command == "prepare":
                    result = prepare_target(client[args.database], args.apply, args.confirm_writes_paused)
                else:
                    result = transfer(client[args.database], args.snapshot, args.run_id,
                                      args.batch_size, args.apply, args.confirm_writes_paused)
        print(json.dumps(result, indent=2))
    except Exception:
        # Driver messages can include DSNs, source values or duplicate personal IDs.
        raise SystemExit("Transfer stopped. No cutover was performed; inspect the private artifacts and source before retrying.") from None


if __name__ == "__main__":
    main()
