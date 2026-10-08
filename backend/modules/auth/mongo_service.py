"""MongoDB authentication with stable UUIDs and transactional first-user bootstrap."""
from datetime import datetime, timezone
from functools import wraps
from uuid import uuid4

from fastapi import HTTPException
import pymongo
from pymongo import ReturnDocument, ReadPreference
from pymongo.errors import DuplicateKeyError, PyMongoError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from backend.config.security import create_access_token, hash_password, verify_password
from backend.modules.auth.service import _verify_google_credential
from backend.db.mongo.init_db import MIGRATION_ID, load_spec

SCHEMA_CHECKSUM = load_spec()[1]

PUBLIC_FIELDS = {"_id": 1, "name": 1, "email": 1, "role": 1, "provider": 1, "is_active": 1}


def normalize_email(email):
    return email.strip().lower()


def serialize_user(document):
    return {"id": document["_id"], **{field: document[field] for field in
            ("name", "email", "role", "provider", "is_active")}}


def auth_response(document):
    user = serialize_user(document)
    return {"access_token": create_access_token({"sub": user["id"], "email": user["email"], "role": user["role"]}),
            "user": user}


def database_errors(function):
    @wraps(function)
    def wrapped(self, *args, **kwargs):
        try:
            # An overall deadline also bounds the driver's transaction retry loop.
            with pymongo.timeout(self.database.client.options.timeout or 5.0):
                return function(self, *args, **kwargs)
        except DuplicateKeyError as error:
            detail = "Email already exists."
            if error.details and "google_id" in error.details.get("keyPattern", {}):
                detail = "This Google identity is already registered with another email."
            raise HTTPException(409, detail) from None
        except PyMongoError:
            raise HTTPException(503, "MongoDB authentication is unavailable. Check the service and schema setup.") from None
    return wrapped


class MongoAuthService:
    def __init__(self, database, *, verify_google=None):
        self.database = database
        self.verify_google = verify_google or _verify_google_credential

    @database_errors
    def check_ready(self):
        migration = self.database.schema_migrations.find_one({"_id": MIGRATION_ID})
        state = self.database.app_metadata.find_one({"_id": "auth_bootstrap"})
        if (not migration or migration.get("version") != 1
                or migration.get("checksum") != SCHEMA_CHECKSUM or not state):
            raise HTTPException(503, "MongoDB authentication schema/bootstrap setup is incomplete.")
        if not state["claimed"] and self.database.users.find_one({}, {"_id": 1}) is not None:
            raise HTTPException(503, "Imported authentication bootstrap must be finalized before signup.")

    def _transaction(self, callback):
        with self.database.client.start_session() as session:
            return session.with_transaction(callback, read_concern=ReadConcern("snapshot"),
                                            write_concern=WriteConcern("majority"),
                                            read_preference=ReadPreference.PRIMARY,
                                            max_commit_time_ms=5000)

    def _insert_user(self, document, requested_role, session):
        state = self.database.app_metadata.find_one({"_id": "auth_bootstrap"}, session=session)
        if state is None:
            raise HTTPException(503, "Authentication bootstrap is not initialized. Run schema/auth setup first.")
        claim = None
        if not state["claimed"]:
            # A partial import must never accidentally bootstrap an additional admin.
            if self.database.users.find_one({}, {"_id": 1}, session=session) is not None:
                raise HTTPException(503, "Imported authentication bootstrap must be finalized before signup.")
            claim = self.database.app_metadata.find_one_and_update(
                {"_id": "auth_bootstrap", "claimed": False},
                {"$set": {"claimed": True, "administrator_id": document["_id"],
                          "updated_at": document["created_at"]}},
                return_document=ReturnDocument.BEFORE, session=session)
        created = {**document, "role": "super_admin" if claim else requested_role}
        self.database.users.insert_one(created, session=session)
        return created

    @database_errors
    def register_user(self, *, name, email, password, requested_role):
        email = normalize_email(email)
        if self.database.users.find_one({"email": email}, {"_id": 1}):
            raise HTTPException(409, "Email already exists.")
        now = datetime.now(timezone.utc)
        document = {"_id": str(uuid4()), "schema_version": 1, "name": name, "email": email,
                    "provider": "local", "password_hash": hash_password(password), "is_active": True,
                    "created_at": now, "updated_at": now}
        created = self._transaction(lambda session: self._insert_user(document, requested_role, session))
        return auth_response(created)

    @database_errors
    def check_email_availability(self, email):
        email = normalize_email(email)
        existing = self.database.users.find_one({"email": email}, {"_id": 1})
        return {"email": email, "isAvailable": existing is None,
                "message": "Email is available." if existing is None else "An account already exists for this email."}

    @staticmethod
    def _check_role(document, requested_role):
        effective = "admin" if document["role"] == "super_admin" else document["role"]
        if effective != requested_role:
            raise HTTPException(403, "Selected role does not match this account.")

    @database_errors
    def login_user(self, *, email, password, requested_role):
        document = self.database.users.find_one({"email": normalize_email(email)})
        if (not document or document["provider"] != "local"
                or not verify_password(password, document.get("password_hash", ""))):
            raise HTTPException(401, "Invalid email or password.")
        self._check_role(document, requested_role)
        # Preserve current is_active behavior; account disabling is a separate policy change.
        return auth_response(document)

    def login_with_google(self, *, credential, requested_role):
        # Network verification runs once, outside the retryable transaction callback.
        payload = self.verify_google(credential)
        return self._login_google_payload(payload, requested_role)

    @database_errors
    def _login_google_payload(self, payload, requested_role):
        email = normalize_email(payload["email"])
        google_id = payload["sub"]
        now = datetime.now(timezone.utc)
        document = {"_id": str(uuid4()), "schema_version": 1,
                    "name": payload.get("name") or email.split("@")[0], "email": email,
                    "provider": "google", "google_id": google_id, "is_active": True,
                    "created_at": now, "updated_at": now}

        def save(session):
            existing = self.database.users.find_one({"email": email}, session=session)
            if existing:
                self._check_role(existing, requested_role)
                if existing["provider"] == "local":
                    raise HTTPException(409, "This email is registered with password login. Use email and password instead.")
                return self.database.users.find_one_and_update({"_id": existing["_id"]}, {"$set": {
                    "name": payload.get("name") or existing["name"], "google_id": google_id,
                    "provider": "google", "updated_at": now,
                }}, return_document=ReturnDocument.AFTER, session=session)
            # Unique Google identity is independently enforced even when email changes.
            if self.database.users.find_one({"google_id": google_id}, {"_id": 1}, session=session):
                raise HTTPException(409, "This Google identity is already registered with another email.")
            return self._insert_user(document, requested_role, session)

        return auth_response(self._transaction(save))

    @database_errors
    def get_user_by_id(self, user_id):
        document = self.database.users.find_one({"_id": str(user_id)}, PUBLIC_FIELDS)
        if document is None:
            raise HTTPException(404, "User not found.")
        return serialize_user(document)
