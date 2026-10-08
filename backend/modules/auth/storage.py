"""Select one auth store per application process; never fall back after a DB failure."""
from fastapi import Request

from backend.config.mongo import get_mongo_database
from backend.modules.auth import service as postgres_service
from backend.modules.auth.mongo_service import MongoAuthService


def get_auth_service(request: Request):
    if getattr(request.app.state, "auth_storage", "postgres") == "mongo":
        service = MongoAuthService(get_mongo_database(request))
        service.check_ready()
        return service
    return postgres_service
