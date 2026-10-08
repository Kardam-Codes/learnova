"""
File: capture_api_baseline.py
Owner: BOTH CAN ADD
Purpose: Record the PostgreSQL API contracts before changing persistence.
What it is: Read-only in-process HTTP checks with private response fixtures.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx

from backend.config.db import connect
from backend.config.security import create_access_token
from backend.main import app


def response_shape(value):
    if isinstance(value, dict):
        return {key: response_shape(item) for key, item in value.items()}
    if isinstance(value, list):
        return {"type": "array", "length": len(value),
                "first_item": response_shape(value[0]) if value else None}
    if value is None:
        return "null"
    return type(value).__name__


async def capture(run: Path, fixture_name: str = "api-baseline.json") -> None:
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT ON (role) id, email, role FROM users ORDER BY role, created_at")
            identities = cursor.fetchall()
            cursor.execute("SELECT slug FROM courses ORDER BY slug")
            courses = [row[0] for row in cursor.fetchall()]
    checks = []

    async def record(client, method, path, expected, *, role=None, headers=None, payload=None):
        response = await client.request(method, path, headers=headers, json=payload)
        try:
            body = response.json()
        except ValueError:
            body = {"non_json_response": True}
        checks.append({"method": method, "path": path, "role": role,
                       "status": response.status_code, "expected": expected,
                       "pass": response.status_code == expected,
                       "shape": response_shape(body), "response": body})

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with app.router.lifespan_context(app), httpx.AsyncClient(transport=transport, base_url="http://baseline.test") as client:
        await record(client, "GET", "/health", 200)
        await record(client, "GET", "/db/health", 200)
        await record(client, "GET", "/courses", 401)
        await record(client, "GET", "/auth/check-email?email=migration-baseline%40example.com", 200)
        # Pydantic rejects this payload before any service/database mutation.
        await record(client, "POST", "/auth/register", 422, payload={
            "name": "Validation baseline", "email": "migration-baseline@example.com",
            "password": "short", "role": "learner",
        })
        for user_id, email, role in identities:
            token = create_access_token({"sub": str(user_id), "email": email, "role": role})
            headers = {"Authorization": "Bearer " + token}
            await record(client, "GET", "/auth/me", 200, role=role, headers=headers)
            await record(client, "GET", "/courses", 200, role=role, headers=headers)
            admin = role in {"super_admin", "admin", "instructor"}
            for path in ["/admin/courses", "/admin/users", "/admin/reports/course-progress"]:
                await record(client, "GET", path, 200 if admin else 403, role=role, headers=headers)
            for slug in courses:
                await record(client, "GET", f"/courses/{slug}", 200, role=role, headers=headers)
                await record(client, "GET", f"/courses/{slug}/reviews", 200, role=role, headers=headers)
                if admin:
                    for suffix in ["", "/attendees", "/content", "/quizzes"]:
                        await record(client, "GET", f"/admin/courses/{slug}{suffix}", 200,
                                     role=role, headers=headers)
    output = run / fixture_name
    output.write_text(json.dumps({"note": "Private source response fixtures; tokens and request auth headers are not stored.",
                                  "checks": checks}, indent=2) + "\n", encoding="utf-8")
    failed = [{key: item[key] for key in ["method", "path", "role", "status", "expected"]}
              for item in checks if not item["pass"]]
    print(json.dumps({"fixture_file": str(output), "checks": len(checks),
                      "passed": len(checks) - len(failed), "failed": failed}, indent=2))
    if failed:
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-directory", required=True, type=Path)
    parser.add_argument("--fixture-name", default="api-baseline.json",
                        choices=["api-baseline.json", "restored-api-baseline.json", "phase2-api-baseline.json",
                                 "phase3-postgres-api-baseline.json", "phase3-mongo-api-baseline.json",
                                 "phase4-postgres-api-baseline.json", "phase4-mongo-api-baseline.json",
                                 "phase5-postgres-api-baseline.json", "phase5-mongo-api-baseline.json",
                                 "phase6-postgres-api-baseline.json", "phase6-mongo-api-baseline.json",
                                 "phase7-postgres-api-baseline.json", "phase7-mongo-api-baseline.json"])
    arguments = parser.parse_args()
    run = arguments.run_directory.resolve()
    private_root = (ROOT / ".local" / "migration-baseline").resolve()
    if not run.is_relative_to(private_root) or not (run / "manifest.json").is_file():
        parser.error("Use an existing private migration baseline run directory.")
    asyncio.run(capture(run, arguments.fixture_name))


if __name__ == "__main__":
    main()
