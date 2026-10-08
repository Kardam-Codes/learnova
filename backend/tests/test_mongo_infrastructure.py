from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from pymongo.errors import DuplicateKeyError, InvalidOperation, WriteError
import pytest

from backend.config.env import load_local_env_file
from backend.db.mongo.init_db import SchemaDriftError, initialize_database, load_spec, assert_development_database
from backend.db.mongo.seed import fixture_documents, seed_database, fixture_id, DEMO_PASSWORD
from backend.config.security import verify_password
from backend.main import app
from backend.tests.conftest import isolated_database


COLLECTIONS = list(load_spec()[0]["collections"])


@pytest.mark.parametrize("collection", COLLECTIONS)
def test_validators_reject_incomplete_documents(database, collection):
    with pytest.raises(WriteError) as error:
        database[collection].insert_one({"_id": str(uuid4())})
    assert error.value.code == 121


def test_repeat_initialization_preserves_data_and_indexes(database):
    before = {name: (database[name].count_documents({}), list(database[name].list_indexes()))
              for name in database.list_collection_names()}
    result = initialize_database(database)
    assert result["collections"] == 16 and result["named_indexes"] == 28
    assert before == {name: (database[name].count_documents({}), list(database[name].list_indexes()))
                      for name in database.list_collection_names()}


def test_duplicate_email_and_optional_provider_identifier(database):
    user = fixture_documents()["users"][0]
    user["_id"] = str(uuid4())
    with pytest.raises(DuplicateKeyError):
        database.users.insert_one(user)
    user["email"] = "other@learnova.example"
    database.users.insert_one(user)  # All local users may omit google_id.
    google = {**user, "_id": str(uuid4()), "email": "google@learnova.example",
              "provider": "google", "google_id": "same-provider-id"}
    database.users.insert_one(google)
    with pytest.raises(DuplicateKeyError):
        database.users.insert_one({**google, "_id": str(uuid4()), "email": "second@learnova.example"})
    with pytest.raises(WriteError):
        database.users.insert_one({**user, "_id": str(uuid4()), "email": "null@learnova.example", "google_id": None})


@pytest.mark.parametrize("collection,changes", [
    ("users", {"provider": "google"}),
    ("courses", {"access_rule": "payment", "price_paise": 0}),
    ("courses", {"price_paise": 99.99}),
    ("course_content", {"content_type": "lesson", "content_mode": "quiz"}),
])
def test_cross_field_and_money_validation(database, collection, changes):
    document = deepcopy(fixture_documents()[collection][0])
    document.update(changes)
    with pytest.raises(WriteError) as error:
        database[collection].replace_one({"_id": document["_id"]}, document)
    assert error.value.code == 121


def test_multidocument_commit_and_rollback(database):
    learner = fixture_id("learner")
    points = {"_id": str(uuid4()), "schema_version": 1, "user_id": learner,
              "total_points": 10, "current_badge": "Newbie", "updated_at": datetime.now(timezone.utc)}
    # The second write is deliberately invalid: the preceding balance must roll back.
    with pytest.raises(WriteError):
        with database.client.start_session() as session:
            with session.start_transaction():
                database.learner_points.insert_one(points, session=session)
                database.point_events.insert_one({"_id": str(uuid4())}, session=session)
    assert database.learner_points.count_documents({}) == 0
    assert database.point_events.count_documents({}) == 0
    tag = {"_id": str(uuid4()), "schema_version": 1, "name": "Transaction",
           "normalized_name": "transaction", "created_at": datetime.now(timezone.utc)}
    with database.client.start_session() as session:
        with session.start_transaction():
            database.learner_points.insert_one(points, session=session)
            database.tags.insert_one(tag, session=session)
    assert database.learner_points.find_one({"_id": points["_id"]})["total_points"] == 10
    assert database.tags.find_one({"_id": tag["_id"]})["created_at"].utcoffset().total_seconds() == 0


@pytest.mark.parametrize("drift", ["validator", "index", "checksum"])
def test_drift_is_reported_without_silent_repair(database, drift):
    if drift == "validator":
        database.command({"collMod": "users", "validationAction": "warn"})
    elif drift == "index":
        database.users.drop_index("uq_users_email")
        database.users.create_index("email", name="uq_users_email", unique=False)
    else:
        database.schema_migrations.update_one({}, {"$set": {"checksum": "changed"}})
    before = (list(database.users.list_indexes()), database.users.options(), list(database.schema_migrations.find()))
    with pytest.raises(SchemaDriftError):
        initialize_database(database)
    assert before == (list(database.users.list_indexes()), database.users.options(), list(database.schema_migrations.find()))


def test_seed_cannot_replace_existing_data(database):
    with pytest.raises(RuntimeError, match="empty"):
        seed_database(database)
    assert database.users.count_documents({}) == 3
    assert verify_password(DEMO_PASSWORD, database.users.find_one()["password_hash"])


@pytest.mark.parametrize("name", ["learnova", "admin", "unrelated", "learnova_test_existing"])
def test_setup_rejects_unsafe_database_names(name):
    with pytest.raises(ValueError):
        assert_development_database(name)


def test_client_lifecycle_and_readiness(database, monkeypatch):
    monkeypatch.setenv("MONGODB_DB", database.name)
    with TestClient(app) as http:
        client = app.state.mongo_client
        assert http.get("/health").status_code == 200
        response = http.get("/mongo/health")
        assert response.json() == {"status": "ok", "database": database.name}
        # Keep the existing response fields and check both configured dependencies.
        monkeypatch.setattr("backend.modules.auth.router.check_database_health",
                            lambda: {"status": "ok", "database": "learnova", "user": "postgres"})
        assert http.get("/db/health").json()["mongodb"]["status"] == "ok"
    assert app.state.mongo_client is None
    with pytest.raises(InvalidOperation):
        client.admin.command("ping")


def test_unavailable_mongo_is_json_503_and_does_not_break_liveness(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "mongodb://private-user:private-password@localhost:1/?replicaSet=missing")
    monkeypatch.setenv("MONGODB_DB", "learnova_migration_dev")
    monkeypatch.setenv("MONGODB_TIMEOUT_MS", "300")
    monkeypatch.setattr("backend.modules.auth.router.check_database_health",
                        lambda: {"status": "ok", "database": "learnova", "user": "postgres"})
    with TestClient(app) as http:
        assert http.get("/health").status_code == 200
        for path in ("/mongo/health", "/db/health"):
            response = http.get(path)
            assert response.status_code == 503 and "detail" in response.json()
            assert "private-" not in response.text and "mongodb://" not in response.text


def test_environment_loader_is_independent_of_database(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text("\ufeffPHASE2_PROVIDER_SETTING=loaded\nPHASE2_OVERRIDE=from-file\n", encoding="utf-8")
    monkeypatch.delenv("PHASE2_PROVIDER_SETTING", raising=False)
    monkeypatch.setenv("PHASE2_OVERRIDE", "from-process")
    load_local_env_file(path)
    import os
    assert os.environ["PHASE2_PROVIDER_SETTING"] == "loaded"
    assert os.environ["PHASE2_OVERRIDE"] == "from-process"
    monkeypatch.delenv("PHASE2_PROVIDER_SETTING")


def test_optional_payment_identifier_uniqueness(database):
    order = {"_id": str(uuid4()), "schema_version": 1, "course_id": fixture_id("course-payment"),
             "user_id": fixture_id("learner"), "provider": "razorpay", "provider_order_id": "order-1",
             "amount_paise": 9900, "currency": "INR", "status": "created", "created_at": datetime.now(timezone.utc)}
    database.payment_orders.insert_one(order)
    database.payment_orders.insert_one({**order, "_id": str(uuid4()), "provider_order_id": "order-2"})
    database.payment_orders.update_one({"_id": order["_id"]}, {"$set": {"provider_payment_id": "payment-1"}})
    with pytest.raises(DuplicateKeyError):
        database.payment_orders.insert_one({**order, "_id": str(uuid4()), "provider_order_id": "order-3", "provider_payment_id": "payment-1"})
    with pytest.raises(WriteError):
        database.payment_orders.insert_one({**order, "_id": str(uuid4()), "provider_order_id": "order-4", "provider_payment_id": None})


def test_attempt_retry_key_uniqueness_and_legacy_missing_keys(database):
    attempt = {"_id": str(uuid4()), "schema_version": 1, "quiz_id": fixture_id("quiz"),
               "user_id": fixture_id("learner"), "attempt_number": 1, "score": 100.0,
               "points_earned": 10, "submitted_at": datetime.now(timezone.utc), "answers": [], "quiz_version": None}
    database.quiz_attempts.insert_one(attempt)
    database.quiz_attempts.insert_one({**attempt, "_id": str(uuid4()), "attempt_number": 2})
    database.quiz_attempts.insert_one({**attempt, "_id": str(uuid4()), "attempt_number": 3, "submission_key": "stable-key"})
    with pytest.raises(DuplicateKeyError):
        database.quiz_attempts.insert_one({**attempt, "_id": str(uuid4()), "attempt_number": 4, "submission_key": "stable-key"})


def test_unversioned_populated_database_is_not_adopted(database):
    database.schema_migrations.delete_many({})
    with pytest.raises(SchemaDriftError, match="Unversioned populated"):
        initialize_database(database)
    assert database.users.count_documents({}) == 3
