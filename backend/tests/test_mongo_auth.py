"""Authentication integration tests against the actual replica set and HTTP routes."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from threading import Barrier
from urllib import error
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from backend.config.security import create_access_token, decode_access_token
from backend.db.mongo.bootstrap import initialize_auth_bootstrap
from backend.db.mongo.seed import DEMO_PASSWORD, fixture_documents, fixture_id
from backend.main import app
from backend.modules.auth.mongo_service import MongoAuthService
from backend.modules.auth.service import _verify_google_credential
from backend.tests.conftest import isolated_database

PASSWORD = "StrongPassword!123"


@pytest.fixture
def auth(database):
    return MongoAuthService(database)


@pytest.fixture
def auth_http(database, monkeypatch):
    monkeypatch.setenv("AUTH_STORAGE", "mongo")
    monkeypatch.setenv("MONGODB_DB", database.name)
    with TestClient(app) as client:
        yield client


def bearer(user_id, *, role="learner", email="learner@learnova.example", expires=3600):
    return {"Authorization": "Bearer " + create_access_token(
        {"sub": user_id, "role": role, "email": email}, expires_in_seconds=expires)}


def test_signup_login_and_me_preserve_contract(auth_http, database):
    result = auth_http.post("/auth/register", json={"name": "New learner", "email": "NewUser@Learnova.Example",
                                                   "password": PASSWORD, "role": "learner"})
    assert result.status_code == 200
    response = result.json()
    assert set(response) == {"access_token", "token_type", "user"} and response["token_type"] == "bearer"
    user = response["user"]
    assert set(user) == {"id", "name", "email", "role", "provider", "is_active"}
    assert user["email"] == "newuser@learnova.example" and user["role"] == "learner"
    assert decode_access_token(response["access_token"])["sub"] == user["id"]
    stored = database.users.find_one({"_id": user["id"]})
    assert stored["password_hash"] != PASSWORD and "google_id" not in stored
    assert stored["created_at"].tzinfo is not None
    login = auth_http.post("/auth/login", json={"email": "NEWUSER@LEARNOVA.EXAMPLE", "password": PASSWORD, "role": "learner"})
    assert login.status_code == 200 and login.json()["user"] == user
    me = auth_http.get("/auth/me", headers={"Authorization": "Bearer " + response["access_token"]})
    assert me.status_code == 200 and me.json() == user
    assert "password_hash" not in result.text and "google_id" not in result.text and "_id" not in result.text


@pytest.mark.parametrize("email,password,role,status", [
    ("learner@learnova.example", DEMO_PASSWORD, "learner", 200),
    ("super_admin@learnova.example", DEMO_PASSWORD, "admin", 200),
    ("instructor@learnova.example", DEMO_PASSWORD, "instructor", 200),
    ("learner@learnova.example", "incorrect", "learner", 401),
    ("missing@learnova.example", DEMO_PASSWORD, "learner", 401),
    ("learner@learnova.example", DEMO_PASSWORD, "admin", 403),
])
def test_migrated_hash_and_selected_role(auth_http, database, email, password, role, status):
    before = list(database.users.find().sort("_id", 1))
    result = auth_http.post("/auth/login", json={"email": email, "password": password, "role": role})
    assert result.status_code == status
    assert list(database.users.find().sort("_id", 1)) == before
    if status == 200:
        assert result.json()["user"]["id"] == next(u["_id"] for u in before if u["email"] == email)


def test_normalized_availability_and_duplicate_email(auth_http, auth):
    check = auth_http.get("/auth/check-email", params={"email": "LEARNER@LEARNOVA.EXAMPLE"})
    assert check.json() == {"email": "learner@learnova.example", "isAvailable": False,
                            "message": "An account already exists for this email."}
    assert auth.check_email_availability("  AVAILABLE@LEARNOVA.EXAMPLE ")["isAvailable"]
    duplicate = auth_http.post("/auth/register", json={"name": "Duplicate", "email": "LEARNER@LEARNOVA.EXAMPLE",
                                                       "password": PASSWORD, "role": "learner"})
    assert duplicate.status_code == 409 and duplicate.json()["detail"] == "Email already exists."


def test_bad_registration_remains_422(auth_http, database):
    response = auth_http.post("/auth/register", json={"name": "Invalid", "email": "invalid@learnova.example",
                                                      "password": "short", "role": "learner"})
    assert response.status_code == 422 and isinstance(response.json()["detail"], list)
    assert database.users.count_documents({}) == 3


@pytest.mark.parametrize("header,status", [
    ({}, 401), ({"Authorization": "Basic bad"}, 401), ({"Authorization": "Bearer invalid"}, 401),
    (bearer(fixture_id("learner"), expires=-60), 401),
    (bearer(str(uuid4())), 404),
])
def test_token_failures(auth_http, header, status):
    assert auth_http.get("/auth/me", headers=header).status_code == status


def test_tampered_and_malformed_signed_token_payloads(auth_http):
    token = create_access_token({"sub": fixture_id("learner"), "email": "learner@learnova.example", "role": "learner"})
    parts = token.split(".")
    parts[1] = parts[1][:-2] + "AA"
    assert auth_http.get("/auth/me", headers={"Authorization": "Bearer " + ".".join(parts)}).status_code == 401
    missing_subject = create_access_token({"email": "learner@learnova.example", "role": "learner"})
    assert auth_http.get("/auth/me", headers={"Authorization": "Bearer " + missing_subject}).status_code == 401
    malformed_expiry = create_access_token({"sub": fixture_id("learner"), "email": "learner@learnova.example", "role": "learner"})
    from unittest.mock import patch
    with patch("backend.modules.auth.dependencies.decode_access_token", return_value=[]):
        assert auth_http.get("/auth/me", headers={"Authorization": "Bearer " + malformed_expiry}).status_code == 401


def test_current_database_role_controls_authorization(auth_http, database):
    # A signed admin role cannot override the persisted learner role.
    response = auth_http.get("/admin/users", headers=bearer(fixture_id("learner"), role="admin"))
    assert response.status_code == 403
    database.users.delete_one({"_id": fixture_id("learner")})
    assert auth_http.get("/auth/me", headers=bearer(fixture_id("learner"))).status_code == 404


def test_inactive_flag_behavior_matches_existing_application(auth_http, database):
    database.users.update_one({"_id": fixture_id("learner")}, {"$set": {"is_active": False}})
    response = auth_http.post("/auth/login", json={"email": "learner@learnova.example", "password": DEMO_PASSWORD, "role": "learner"})
    assert response.status_code == 200 and response.json()["user"]["is_active"] is False
    assert auth_http.get("/auth/me", headers=bearer(fixture_id("learner"))).json()["is_active"] is False


def test_google_create_update_and_password_collision(auth_http, database, monkeypatch):
    payload = {"email": "Google@Learnova.Example", "sub": "provider-id", "name": "Google learner"}
    monkeypatch.setattr("backend.modules.auth.mongo_service._verify_google_credential", lambda credential: payload)
    first = auth_http.post("/auth/google", json={"credential": "controlled-google-token", "role": "learner"})
    assert first.status_code == 200 and first.json()["user"]["provider"] == "google"
    identifier = first.json()["user"]["id"]
    stored = database.users.find_one({"_id": identifier})
    assert "password_hash" not in stored and stored["google_id"] == "provider-id"
    payload["name"] = "Updated name"
    second = auth_http.post("/auth/google", json={"credential": "controlled-google-token", "role": "learner"})
    assert second.json()["user"]["id"] == identifier and second.json()["user"]["name"] == "Updated name"
    assert database.users.find_one({"_id": identifier})["created_at"] == stored["created_at"]
    assert "google_id" not in second.text
    assert auth_http.post("/auth/login", json={"email": payload["email"], "password": PASSWORD, "role": "learner"}).status_code == 401
    assert auth_http.post("/auth/google", json={"credential": "controlled-google-token", "role": "instructor"}).status_code == 403
    payload["email"] = "learner@learnova.example"
    assert auth_http.post("/auth/google", json={"credential": "controlled-google-token", "role": "learner"}).status_code == 409


def test_google_identity_collision_never_creates_second_account(auth, database):
    payload = {"email": "first@learnova.example", "sub": "one-provider-id"}
    auth.verify_google = lambda credential: payload
    first = auth.login_with_google(credential="controlled-google-token", requested_role="learner")
    payload["email"] = "second@learnova.example"
    with pytest.raises(HTTPException) as conflict:
        auth.login_with_google(credential="controlled-google-token", requested_role="learner")
    assert conflict.value.status_code == 409
    assert database.users.count_documents({"google_id": "one-provider-id"}) == 1
    assert database.users.find_one({"_id": first["user"]["id"]})["email"] == "first@learnova.example"


def test_google_verification_runs_once_when_transaction_retries(mongo_client, monkeypatch):
    from pymongo.errors import OperationFailure
    with isolated_database(mongo_client) as database:
        initialize_auth_bootstrap(database)
        calls = {"verify": 0, "insert": 0}
        def verify(credential):
            calls["verify"] += 1
            return {"email": "retry@learnova.example", "sub": "retry-google-id"}
        auth = MongoAuthService(database, verify_google=verify)
        original = auth._insert_user
        def insert(document, role, session):
            created = original(document, role, session)
            calls["insert"] += 1
            if calls["insert"] == 1:
                raise OperationFailure("injected transient transaction failure", 112,
                                       {"errorLabels": ["TransientTransactionError"]})
            return created
        monkeypatch.setattr(auth, "_insert_user", insert)
        result = auth.login_with_google(credential="controlled-google-token", requested_role="learner")
        assert calls == {"verify": 1, "insert": 2}
        assert database.users.count_documents({}) == 1
        assert database.app_metadata.find_one()["administrator_id"] == result["user"]["id"]


def test_first_user_bootstrap_and_no_reopening(mongo_client):
    with isolated_database(mongo_client) as database:
        initialize_auth_bootstrap(database)
        auth = MongoAuthService(database)
        first = auth.register_user(name="First", email="first@learnova.example", password=PASSWORD, requested_role="learner")
        assert first["user"]["role"] == "super_admin"
        assert auth.login_user(email="first@learnova.example", password=PASSWORD, requested_role="admin")["user"] == first["user"]
        database.users.delete_many({})
        initialize_auth_bootstrap(database)
        next_user = auth.register_user(name="Next", email="next@learnova.example", password=PASSWORD, requested_role="learner")
        assert next_user["user"]["role"] == "learner"


@pytest.mark.parametrize("kind", ["local", "google"])
def test_simultaneous_first_signups_have_exactly_one_bootstrap_admin(mongo_client, monkeypatch, kind):
    with isolated_database(mongo_client) as database:
        initialize_auth_bootstrap(database)
        auth = MongoAuthService(database, verify_google=lambda credential: {"email": credential + "@learnova.example", "sub": credential})
        barrier = Barrier(2)
        original = auth._transaction
        def synchronized(callback):
            barrier.wait(timeout=10)
            return original(callback)
        monkeypatch.setattr(auth, "_transaction", synchronized)
        def signup(number):
            if kind == "google":
                return auth.login_with_google(credential="google-" + str(number), requested_role="learner")
            return auth.register_user(name="Concurrent", email=f"user-{number}@learnova.example", password=PASSWORD, requested_role="learner")
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(signup, (1, 2)))
        assert sorted(result["user"]["role"] for result in results) == ["learner", "super_admin"]
        assert database.users.count_documents({}) == 2
        administrator = database.users.find_one({"role": "super_admin"})
        assert database.app_metadata.find_one()["administrator_id"] == administrator["_id"]


def test_simultaneous_duplicate_email_is_409(auth, database, monkeypatch):
    barrier = Barrier(2)
    original = auth._transaction
    def synchronized(callback):
        barrier.wait(timeout=10)
        return original(callback)
    monkeypatch.setattr(auth, "_transaction", synchronized)
    def signup(email):
        try:
            auth.register_user(name="Race", email=email, password=PASSWORD, requested_role="learner")
            return 200
        except HTTPException as exc:
            return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(signup, ("race@learnova.example", "RACE@LEARNOVA.EXAMPLE")))
    assert sorted(statuses) == [200, 409]
    assert database.users.count_documents({"email": "race@learnova.example"}) == 1


def test_failed_user_insert_rolls_back_bootstrap_claim(mongo_client):
    with isolated_database(mongo_client) as database:
        initialize_auth_bootstrap(database)
        auth = MongoAuthService(database)
        with pytest.raises(HTTPException) as failure:
            auth.register_user(name=None, email="invalid@learnova.example", password=PASSWORD, requested_role="learner")
        assert failure.value.status_code == 503
        assert database.users.count_documents({}) == 0
        assert database.app_metadata.find_one()["claimed"] is False
        assert database.app_metadata.find_one()["administrator_id"] is None


def test_imported_users_close_bootstrap_and_preserve_identity(mongo_client):
    with isolated_database(mongo_client) as database:
        initialize_auth_bootstrap(database)  # Target was initialized empty before import.
        rows = fixture_documents()["users"]
        database.users.insert_many(deepcopy(rows))
        auth = MongoAuthService(database)
        with pytest.raises(HTTPException):
            auth.check_ready()  # Traffic must not use a partially finalized import.
        initialize_auth_bootstrap(database)
        auth.check_ready()
        created = auth.register_user(name="After import", email="after@learnova.example", password=PASSWORD, requested_role="learner")
        assert created["user"]["role"] == "learner"
        assert database.app_metadata.find_one()["administrator_id"] == fixture_id("super_admin")
        for row in rows:
            assert database.users.find_one({"_id": row["_id"]}) == row


def test_missing_bootstrap_refuses_signup_without_writes(mongo_client):
    with isolated_database(mongo_client) as database:
        auth = MongoAuthService(database)
        with pytest.raises(HTTPException) as error:
            auth.register_user(name="Unprepared", email="unprepared@learnova.example", password=PASSWORD, requested_role="learner")
        assert error.value.status_code == 503 and database.users.count_documents({}) == 0


def test_demo_seed_after_explicit_bootstrap_setup(mongo_client):
    from backend.db.mongo.seed import seed_database
    with isolated_database(mongo_client) as database:
        initialize_auth_bootstrap(database)
        seed_database(database)
        assert database.users.count_documents({}) == 3
        assert database.app_metadata.find_one()["claimed"] is True
        assert database.app_metadata.find_one()["administrator_id"] == fixture_id("super_admin")


def test_mongo_auth_never_opens_postgres(auth_http, monkeypatch):
    def fail(): raise AssertionError("MongoDB auth must not connect to PostgreSQL")
    monkeypatch.setattr("backend.modules.auth.service.connect", fail)
    payload = {"name": "Mongo only", "email": "mongo-only@learnova.example", "password": PASSWORD, "role": "learner"}
    registered = auth_http.post("/auth/register", json=payload)
    assert registered.status_code == 200
    assert auth_http.post("/auth/login", json=payload).status_code == 200
    assert auth_http.get("/auth/check-email", params={"email": payload["email"]}).json()["isAvailable"] is False
    assert auth_http.get("/auth/me", headers={"Authorization": "Bearer " + registered.json()["access_token"]}).status_code == 200
    monkeypatch.setattr("backend.modules.auth.mongo_service._verify_google_credential",
                        lambda credential: {"email": "mongo-google@learnova.example", "sub": "mongo-google-id"})
    assert auth_http.post("/auth/google", json={"credential": "controlled-google-token", "role": "learner"}).status_code == 200


def test_unavailable_mongo_auth_is_503_without_postgres_fallback(monkeypatch):
    monkeypatch.setenv("AUTH_STORAGE", "mongo")
    monkeypatch.setenv("MONGODB_URI", "mongodb://private-user:private-password@localhost:1/?replicaSet=missing")
    monkeypatch.setenv("MONGODB_DB", "learnova_migration_dev")
    monkeypatch.setenv("MONGODB_TIMEOUT_MS", "300")
    def fail(): raise AssertionError("Unavailable MongoDB must not fall back to PostgreSQL")
    monkeypatch.setattr("backend.modules.auth.service.connect", fail)
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        response = client.post("/auth/login", json={"email": "learner@learnova.example", "password": PASSWORD, "role": "learner"},
                               headers={"Origin": "http://localhost:5173"})
        assert response.status_code == 503
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
        assert "private-" not in response.text and "mongodb://" not in response.text


def test_auth_readiness_refuses_missing_bootstrap(mongo_client, monkeypatch):
    with isolated_database(mongo_client) as database:
        monkeypatch.setenv("AUTH_STORAGE", "mongo")
        monkeypatch.setenv("MONGODB_DB", database.name)
        with TestClient(app) as client:
            assert client.get("/health").status_code == 200
            assert client.get("/mongo/health").status_code == 503
            response = client.post("/auth/register", json={"name": "Unprepared", "email": "unprepared@learnova.example",
                                                           "password": PASSWORD, "role": "learner"})
            assert response.status_code == 503 and database.users.count_documents({}) == 0


def test_explicit_postgres_selection_is_stable_for_app_lifetime(monkeypatch):
    monkeypatch.setenv("AUTH_STORAGE", "postgres")
    user = {"id": fixture_id("learner"), "name": "Legacy learner", "email": "learner@learnova.example",
            "role": "learner", "provider": "local", "is_active": True}
    monkeypatch.setattr("backend.modules.auth.service.login_user", lambda **kwargs: {"access_token": "legacy-token", "user": user})
    def fail(*args, **kwargs): raise AssertionError("PostgreSQL mode must not query MongoDB authentication")
    monkeypatch.setattr(MongoAuthService, "login_user", fail)
    with TestClient(app) as client:
        monkeypatch.setenv("AUTH_STORAGE", "mongo")  # Requires restart; does not split in-flight identity stores.
        response = client.post("/auth/login", json={"email": user["email"], "password": PASSWORD, "role": "learner"})
        assert response.status_code == 200 and response.json()["access_token"] == "legacy-token"


@pytest.mark.parametrize("payload", [
    {"aud": "different", "email_verified": "true", "email": "google@learnova.example", "sub": "id"},
    {"aud": "expected", "email_verified": "false", "email": "google@learnova.example", "sub": "id"},
    {"aud": "expected", "email_verified": "true", "email": "google@learnova.example"},
])
def test_google_verification_rejects_bad_claims(monkeypatch, payload):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return json.dumps(payload).encode()
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "expected")
    monkeypatch.setattr("backend.modules.auth.service.request.urlopen", lambda *args, **kwargs: Response())
    with pytest.raises(HTTPException) as rejection:
        _verify_google_credential("controlled-google-token")
    assert rejection.value.status_code == 401


@pytest.mark.parametrize("exception,status", [
    (error.HTTPError("https://oauth2.googleapis.com/tokeninfo", 400, "invalid", None, None), 401),
    (error.URLError("network unavailable"), 502),
])
def test_google_verification_network_failures_are_controlled(monkeypatch, exception, status):
    def fail(*args, **kwargs): raise exception
    monkeypatch.setattr("backend.modules.auth.service.request.urlopen", fail)
    with pytest.raises(HTTPException) as rejection:
        _verify_google_credential("controlled-google-token")
    assert rejection.value.status_code == status
