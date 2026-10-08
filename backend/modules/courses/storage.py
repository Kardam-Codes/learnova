"""Select learner storage for every route; never send MongoDB writes to PostgreSQL."""
from fastapi import Request

from backend.config.mongo import get_mongo_database
from backend.modules.auth.mongo_service import MongoAuthService
from backend.modules.courses import service as postgres_service
from backend.modules.courses.mongo_service import MongoCourseService


def get_course_service(request: Request):
    if getattr(request.app.state, "courses_storage", "postgres") == "mongo":
        database = get_mongo_database(request)
        MongoAuthService(database).check_ready()
        return MongoCourseService(database)
    return postgres_service
