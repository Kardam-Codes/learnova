"""
File: capture_postgres_baseline.py
Owner: BOTH CAN ADD
Purpose: Capture a consistent, private PostgreSQL baseline before migration.
What it is: A read-only source audit and pg_dump backup with checksummed assets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

from backend.config.db import get_database_url


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def table_fingerprints(connection) -> dict:
    """Store only counts/digests, never row values, in the audit manifest."""
    result = {}
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
            "ORDER BY table_name"
        )
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            cursor.execute(sql.SQL("SELECT * FROM public.{}").format(sql.Identifier(table)))
            columns = [column.name for column in cursor.description]
            rows = sorted(
                json.dumps(dict(zip(columns, row)), sort_keys=True, default=str)
                for row in cursor.fetchall()
            )
            digest = hashlib.sha256()
            for row in rows:
                digest.update(row.encode("utf-8"))
                digest.update(b"\n")
            result[table] = {"rows": len(rows), "sha256": digest.hexdigest()}
    return result


def schema_inventory(connection) -> dict:
    queries = {
        "columns": """
            SELECT table_name, column_name, ordinal_position, data_type,
                   udt_name, is_nullable, column_default
            FROM information_schema.columns WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
        """,
        "constraints": """
            SELECT c.relname AS table_name, con.conname AS name,
                   con.contype AS type, pg_get_constraintdef(con.oid) AS definition
            FROM pg_constraint con JOIN pg_class c ON c.oid = con.conrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' ORDER BY c.relname, con.conname
        """,
        "indexes": """
            SELECT tablename, indexname, indexdef FROM pg_indexes
            WHERE schemaname = 'public' ORDER BY tablename, indexname
        """,
        "views": """
            SELECT viewname, definition FROM pg_views
            WHERE schemaname = 'public' ORDER BY viewname
        """,
        "enums": """
            SELECT t.typname, e.enumlabel, e.enumsortorder
            FROM pg_type t JOIN pg_enum e ON e.enumtypid = t.oid
            JOIN pg_namespace n ON n.oid = t.typnamespace
            WHERE n.nspname = 'public' ORDER BY t.typname, e.enumsortorder
        """,
        "extensions": "SELECT extname, extversion FROM pg_extension ORDER BY extname",
    }
    result = {}
    with connection.cursor() as cursor:
        for name, query in queries.items():
            cursor.execute(query)
            columns = [column.name for column in cursor.description]
            result[name] = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return result


def data_audit(connection) -> dict:
    """Return aggregate issues without exposing names, emails, or hashes."""
    checks = {
        "normalized_email_collision_groups": """
            SELECT count(*) FROM (
                SELECT lower(trim(email)) FROM users
                GROUP BY lower(trim(email)) HAVING count(*) > 1
            ) collisions
        """,
        "normalized_tag_collision_groups": """
            SELECT count(*) FROM (
                SELECT lower(trim(name)) FROM course_tags
                GROUP BY lower(trim(name)) HAVING count(*) > 1
            ) collisions
        """,
        "content_slugs_shared_across_courses": """
            SELECT count(*) FROM (
                SELECT slug FROM course_content GROUP BY slug
                HAVING count(DISTINCT course_id) > 1
            ) collisions
        """,
        "quizzes_without_questions": """
            SELECT count(*) FROM quizzes q WHERE NOT EXISTS
            (SELECT 1 FROM quiz_questions qq WHERE qq.quiz_id = q.id)
        """,
        "questions_without_options": """
            SELECT count(*) FROM quiz_questions q WHERE NOT EXISTS
            (SELECT 1 FROM quiz_options o WHERE o.question_id = q.id)
        """,
        "questions_without_correct_options": """
            SELECT count(*) FROM quiz_questions q WHERE NOT EXISTS
            (SELECT 1 FROM quiz_options o WHERE o.question_id = q.id AND o.is_correct)
        """,
        "courses_without_content": """
            SELECT count(*) FROM courses c WHERE NOT EXISTS
            (SELECT 1 FROM course_content cc WHERE cc.course_id = c.id)
        """,
        "progress_completed_count_mismatches": """
            SELECT count(*) FROM course_progress cp WHERE cp.completed_count <>
            (SELECT count(*) FROM content_progress x WHERE x.course_id = cp.course_id
             AND x.user_id = cp.user_id AND x.status = 'completed')
        """,
        "quiz_course_content_mismatches": """
            SELECT count(*) FROM quizzes q JOIN course_content c ON c.id = q.content_id
            WHERE q.course_id <> c.course_id
        """,
        "content_progress_course_mismatches": """
            SELECT count(*) FROM content_progress p JOIN course_content c ON c.id = p.content_id
            WHERE p.course_id <> c.course_id
        """,
        "paid_enrollments_without_paid_order": """
            SELECT count(*) FROM course_attendees e WHERE e.payment_status = 'paid'
            AND NOT EXISTS (SELECT 1 FROM course_payment_orders o
                WHERE o.course_id = e.course_id AND o.user_id = e.user_id AND o.status = 'paid')
        """,
        "users_by_role": "SELECT role::text, count(*) FROM users GROUP BY role ORDER BY role",
        "max_questions_per_quiz": "SELECT coalesce(max(n), 0) FROM (SELECT count(*) n FROM quiz_questions GROUP BY quiz_id) s",
        "max_options_per_question": "SELECT coalesce(max(n), 0) FROM (SELECT count(*) n FROM quiz_options GROUP BY question_id) s",
        "max_attachments_per_content": "SELECT coalesce(max(n), 0) FROM (SELECT count(*) n FROM content_attachments GROUP BY content_id) s",
    }
    result = {}
    with connection.cursor() as cursor:
        for name, query in checks.items():
            cursor.execute(query)
            rows = cursor.fetchall()
            result[name] = dict(rows) if name == "users_by_role" else rows[0][0]
    return result


def resolve_tool(name: str, binary_dir: Path | None) -> str:
    candidate = binary_dir / f"{name}.exe" if binary_dir else None
    if candidate and candidate.is_file():
        return str(candidate)
    resolved = shutil.which(name)
    if not resolved:
        raise RuntimeError(f"{name} was not found; pass --postgres-bin explicitly.")
    return resolved


def pg_environment(url: str) -> tuple[dict, list[str]]:
    settings = conninfo_to_dict(url)
    environment = dict(os.environ)
    # Remove inherited PG settings that could select a different server/database.
    for key in list(environment):
        if key.startswith("PG"):
            environment.pop(key)
    environment["PGPASSWORD"] = settings.get("password", "")
    arguments = [
        "--host", settings.get("host", "localhost"),
        "--port", settings.get("port", "5432"),
        "--username", settings.get("user", "postgres"),
        "--no-password",
    ]
    return environment, arguments


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postgres-bin", type=Path)
    args = parser.parse_args()
    pg_dump = resolve_tool("pg_dump", args.postgres_bin)
    pg_restore = resolve_tool("pg_restore", args.postgres_bin)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run = ROOT / ".local" / "migration-baseline" / stamp
    run.mkdir(parents=True, exist_ok=False)
    url = get_database_url()
    environment, connection_args = pg_environment(url)
    manifest = {
        "status": "incomplete", "created_at_utc": stamp,
        "backup_scope": "Database without role ownership/ACL restoration; uploaded assets and application source separately archived.",
    }
    manifest_path = run / "manifest.json"
    try:
        with psycopg.connect(url) as connection:
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_database(), version(), pg_export_snapshot()")
                database, version, snapshot = cursor.fetchone()
            manifest.update({"database": database, "server_version": version})
            manifest["tables"] = table_fingerprints(connection)
            manifest["schema"] = schema_inventory(connection)
            manifest["audit"] = data_audit(connection)
            subprocess.run(
                [pg_dump, *connection_args, "--dbname", database,
                 "--format=custom", "--no-owner", "--no-acl", "--snapshot", snapshot,
                 "--file", str(run / "database.dump")],
                env=environment, check=True, capture_output=True,
            )
        with (run / "restore-list.txt").open("wb") as output:
            subprocess.run([pg_restore, "--list", str(run / "database.dump")],
                           check=True, stdout=output, stderr=subprocess.PIPE)
        uploads = ROOT / "backend" / "uploads"
        with zipfile.ZipFile(run / "uploads.zip", "w", zipfile.ZIP_DEFLATED) as archive:
            upload_files = []
            for path in sorted(uploads.rglob("*")):
                if path.is_file():
                    relative = path.relative_to(uploads).as_posix()
                    archive.write(path, relative)
                    upload_files.append({"path": relative, "sha256": file_digest(path)})
        manifest["uploads"] = upload_files
        excluded = {"node_modules", "dist", ".git", ".local", "__pycache__", ".venv", "venv"}
        with zipfile.ZipFile(run / "application-source.zip", "w", zipfile.ZIP_DEFLATED) as archive:
            for current, directories, filenames in os.walk(ROOT):
                directories[:] = sorted(d for d in directories if d not in excluded)
                for filename in sorted(filenames):
                    path = Path(current) / filename
                    # Keep credentials out of source archives; the local .env remains untouched.
                    if filename == ".env" or filename.startswith(".env.") and filename != ".env.example":
                        continue
                    if path.suffix == ".pyc":
                        continue
                    archive.write(path, path.relative_to(ROOT).as_posix())
        manifest["artifacts"] = {
            name: {"bytes": (run / name).stat().st_size, "sha256": file_digest(run / name)}
            for name in ["database.dump", "restore-list.txt", "uploads.zip", "application-source.zip"]
        }
        manifest["status"] = "backup_and_audit_complete_restore_pending"
    except Exception as exc:
        manifest["failure_type"] = type(exc).__name__
        raise
    finally:
        manifest_path.write_text(json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"run_directory": str(run), "status": manifest["status"],
                      "table_count": len(manifest["tables"]), "audit": manifest["audit"]}, indent=2))


if __name__ == "__main__":
    main()
