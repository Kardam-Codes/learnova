"""Explicit bootstrap initialization during quiescent setup/import, never on signup."""
from datetime import datetime, timezone


def initialize_auth_bootstrap(database):
    if database.schema_migrations.find_one({"_id": "mongodb-schema-v1"}) is None:
        raise RuntimeError("Initialize the reviewed MongoDB schema before auth bootstrap.")
    existing = database.users.find_one({}, {"_id": 1})
    administrator = database.users.find_one({"role": "super_admin"}, {"_id": 1})
    if administrator is None:
        administrator = database.users.find_one({"role": "admin"}, {"_id": 1})
    now = datetime.now(timezone.utc)
    database.app_metadata.update_one({"_id": "auth_bootstrap"}, {"$setOnInsert": {
        "schema_version": 1, "claimed": existing is not None,
        "administrator_id": administrator["_id"] if administrator else None, "updated_at": now,
    }}, upsert=True)
    # Imports close an already initialized empty target. Never reopen claimed state,
    # even if its users have later been deleted. Run without live signup/import traffic.
    if existing is not None:
        database.app_metadata.update_one({"_id": "auth_bootstrap", "claimed": False}, {"$set": {
            "claimed": True, "administrator_id": administrator["_id"] if administrator else None,
            "updated_at": now,
        }})
    return database.app_metadata.find_one({"_id": "auth_bootstrap"})
