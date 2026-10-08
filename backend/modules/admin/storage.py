"""Select admin authoring and reporting storage explicitly."""
from fastapi import Request

from backend.config.mongo import get_mongo_database
from backend.modules.admin import service as postgres_service
from backend.modules.admin.mongo_service import MongoAdminService
from backend.modules.auth.mongo_service import MongoAuthService


def get_admin_service(request: Request):
    if getattr(request.app.state, "admin_storage", "postgres") == "mongo":
        database = get_mongo_database(request)
        MongoAuthService(database).check_ready()
        return MongoAdminService(database)
    return postgres_service
