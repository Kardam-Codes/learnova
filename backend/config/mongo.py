"""Process-owned synchronous MongoDB client, separate from PostgreSQL export access."""
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import os
import re

from fastapi import HTTPException, Request
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from backend.config.env import load_local_env_file


@dataclass(frozen=True)
class MongoSettings:
    uri: str = field(repr=False)
    database: str
    timeout_ms: int = 5000


def get_mongo_settings() -> MongoSettings | None:
    load_local_env_file()
    uri = os.environ.get("MONGODB_URI", "").strip()
    if not uri:
        return None
    database = os.environ.get("MONGODB_DB", "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", database) or database in {"admin", "config", "local"}:
        raise ValueError("MONGODB_DB must name an application database.")
    timeout = int(os.environ.get("MONGODB_TIMEOUT_MS", "5000"))
    if not 100 <= timeout <= 60000:
        raise ValueError("MONGODB_TIMEOUT_MS must be between 100 and 60000.")
    return MongoSettings(uri=uri, database=database, timeout_ms=timeout)


def create_mongo_client(settings: MongoSettings) -> MongoClient:
    try:
        return MongoClient(
            settings.uri, appname="Learnova", tz_aware=True,
            serverSelectionTimeoutMS=settings.timeout_ms,
            connectTimeoutMS=settings.timeout_ms, socketTimeoutMS=settings.timeout_ms,
            waitQueueTimeoutMS=settings.timeout_ms, timeoutMS=settings.timeout_ms,
            connect=False,
        )
    except (ValueError, PyMongoError):
        raise ValueError("Invalid MongoDB connection configuration.") from None


@asynccontextmanager
async def mongo_lifespan(app):
    # Also initializes Google/payment settings before any PostgreSQL call.
    settings = get_mongo_settings()
    auth_storage = os.environ.get("AUTH_STORAGE", "postgres").strip().lower()
    if auth_storage not in {"postgres", "mongo"}:
        raise ValueError("AUTH_STORAGE must be postgres or mongo.")
    if auth_storage == "mongo" and settings is None:
        raise ValueError("MongoDB authentication requires MONGODB_URI and MONGODB_DB.")
    admin_storage = os.environ.get("ADMIN_STORAGE", "postgres").strip().lower()
    if admin_storage not in {"postgres", "mongo"}:
        raise ValueError("ADMIN_STORAGE must be postgres or mongo.")
    if admin_storage == "mongo" and auth_storage != "mongo":
        raise ValueError("MongoDB admin storage requires MongoDB authentication.")
    courses_storage = os.environ.get("COURSES_STORAGE", "postgres").strip().lower()
    if courses_storage not in {"postgres", "mongo"}:
        raise ValueError("COURSES_STORAGE must be postgres or mongo.")
    if courses_storage == "mongo" and (auth_storage != "mongo" or admin_storage != "mongo"):
        raise ValueError("MongoDB learner storage requires MongoDB authentication and admin storage.")
    client = create_mongo_client(settings) if settings else None
    app.state.mongo_client = client
    app.state.mongo_settings = settings
    app.state.auth_storage = auth_storage
    app.state.admin_storage = admin_storage
    app.state.courses_storage = courses_storage
    try:
        yield
    finally:
        if client is not None:
            client.close()
        app.state.mongo_client = None


def get_mongo_database(request: Request):
    client = getattr(request.app.state, "mongo_client", None)
    settings = getattr(request.app.state, "mongo_settings", None)
    if client is None or settings is None:
        raise HTTPException(503, "MongoDB is not configured or its client is not running.")
    return client[settings.database]


def check_mongo_readiness(request: Request) -> dict:
    database = get_mongo_database(request)
    try:
        database.command("ping")
        hello = database.client.admin.command("hello")
        if not hello.get("setName") or not hello.get("isWritablePrimary"):
            raise HTTPException(503, "MongoDB replica set has no writable primary.")
        if getattr(request.app.state, "auth_storage", "postgres") == "mongo":
            from backend.modules.auth.mongo_service import MongoAuthService
            MongoAuthService(database).check_ready()
        return {"status": "ok", "database": database.name}
    except PyMongoError:
        raise HTTPException(503, "MongoDB is unavailable. Check the local service and replica set.") from None
