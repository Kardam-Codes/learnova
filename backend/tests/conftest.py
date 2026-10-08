"""Real-server integration fixtures. Never reuse or drop an application database."""
from contextlib import contextmanager
import os
import re
from uuid import uuid4

import pytest

from backend.config.mongo import MongoSettings, create_mongo_client, get_mongo_settings
from backend.db.mongo.init_db import initialize_database
from backend.db.mongo.seed import seed_database


@pytest.fixture(scope="session")
def mongo_client():
    settings = get_mongo_settings()
    uri = os.environ.get("MONGODB_TEST_URI") or (settings.uri if settings else "")
    if not uri:
        pytest.fail("A real transaction-capable MongoDB test URI is required; integration tests are not skipped.")
    with create_mongo_client(MongoSettings(uri, "learnova_migration_dev")) as client:
        hello = client.admin.command("hello")
        assert hello.get("setName") and hello.get("isWritablePrimary"), "A writable replica set is required."
        yield client


@contextmanager
def isolated_database(client):
    name = "learnova_test_" + uuid4().hex
    settings = get_mongo_settings()
    application_name = settings.database if settings else None
    assert name != application_name and name not in client.list_database_names()
    assert re.fullmatch(r"learnova_test_[0-9a-f]{32}", name)
    database = client[name]
    try:
        initialize_database(database)
        yield database
    finally:
        # Only this context's generated name is ever passed to drop_database.
        assert re.fullmatch(r"learnova_test_[0-9a-f]{32}", name) and name != application_name
        client.drop_database(name)


@pytest.fixture
def database(mongo_client):
    with isolated_database(mongo_client) as database:
        seed_database(database)
        yield database
