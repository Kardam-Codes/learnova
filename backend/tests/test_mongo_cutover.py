"""MongoDB-only runtime and the migration write pause."""
import os
import subprocess
import sys

from fastapi.testclient import TestClient
from backend.main import app


def test_write_pause_blocks_mutations_and_keeps_reads(monkeypatch):
    monkeypatch.setenv("APPLICATION_WRITES_PAUSED", "true")
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.post("/auth/register", json={}).status_code == 503
        assert client.post("/admin/uploads").status_code == 503
        assert client.post("/auth/login", json={}).status_code == 422


def test_runtime_starts_and_reads_mongo_when_postgres_driver_is_unavailable(database):
    script = '''
import importlib.abc, sys
class BlockPostgres(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'psycopg', 'psycopg2'}:
            raise ImportError('PostgreSQL intentionally unavailable')
sys.meta_path.insert(0, BlockPostgres())
from backend.main import app
from backend.config import db
def forbidden(*args, **kwargs):
    raise AssertionError('Mongo runtime attempted PostgreSQL access')
db.connect = forbidden
from fastapi.testclient import TestClient
from backend.tests.test_mongo_auth import bearer
from backend.db.mongo.seed import fixture_id
with TestClient(app) as client:
    assert client.get('/db/health').status_code == 200
    client.headers.update(bearer(fixture_id('learner')))
    assert client.get('/courses').status_code == 200
    client.headers.update(bearer(fixture_id('instructor'), role='instructor', email='instructor@learnova.example'))
    assert client.get('/admin/reports/course-progress').status_code == 200
    assert client.get('/admin/courses').status_code == 200
print('MongoDB-only runtime checks passed')
'''
    env = {**os.environ, "AUTH_STORAGE": "mongo", "ADMIN_STORAGE": "mongo",
           "COURSES_STORAGE": "mongo", "MONGODB_DB": database.name,
           "APPLICATION_WRITES_PAUSED": "false"}
    result = subprocess.run([sys.executable, "-c", script], env=env,
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
