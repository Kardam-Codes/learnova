"""
File: router.py
Owner: BOTH CAN ADD
Created: 2026-03-21
Project: Learnova (eLearning Platform)
Purpose: Expose the initial auth and DB health API routes.
What it is: A FastAPI router for auth endpoints and basic backend connectivity checks.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from backend.config.mongo import check_mongo_readiness
from pydantic import EmailStr

from backend.modules.auth.dependencies import get_current_token_payload
from backend.modules.auth.storage import get_auth_service
from backend.modules.auth.schemas import (
    AuthResponse,
    EmailAvailabilityResponse,
    GoogleAuthRequest,
    LoginRequest,
    RegisterRequest,
    TokenPayload,
    UserResponse,
)
from backend.modules.auth.service import check_database_health


router = APIRouter(tags=["auth"])


@router.get("/db/health", tags=["system"])
def db_health(request: Request):
    """
    This route confirms that PostgreSQL is reachable from the backend layer.
    """

    if getattr(request.app.state, "auth_storage", "postgres") == "mongo":
        return {"status": "ok", "database": "mongodb", "mongodb": check_mongo_readiness(request)}
    from psycopg import Error as PostgresError
    try:
        result = check_database_health()
    except PostgresError:
        raise HTTPException(503, "PostgreSQL is unavailable. Check the local service and configuration.") from None
    # During phased conversion the API still depends on PostgreSQL. Include the
    # configured MongoDB target as an additive readiness result until cutover.
    if getattr(request.app.state, "mongo_settings", None) is not None:
        result["mongodb"] = check_mongo_readiness(request)
    return result


@router.post("/auth/register", response_model=AuthResponse)
def register(payload: RegisterRequest, auth=Depends(get_auth_service)):
    """
    This creates a local user account and returns a bearer token for the new session.
    """

    return auth.register_user(
        name=payload.name,
        email=payload.email,
        password=payload.password,
        requested_role=payload.role,
    )


@router.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, auth=Depends(get_auth_service)):
    """
    This authenticates an existing local user against the configured authentication store.
    """

    return auth.login_user(
        email=payload.email,
        password=payload.password,
        requested_role=payload.role,
    )


@router.post("/auth/google", response_model=AuthResponse)
def google_login(payload: GoogleAuthRequest, auth=Depends(get_auth_service)):
    """
    This verifies a Google credential on the backend and returns a Learnova session token.
    """

    return auth.login_with_google(
        credential=payload.credential,
        requested_role=payload.role,
    )


@router.get("/auth/check-email", response_model=EmailAvailabilityResponse)
def check_email(email: EmailStr, auth=Depends(get_auth_service)):
    """
    This validates whether an account already exists for the supplied email.
    """

    return auth.check_email_availability(str(email))


@router.get("/auth/me", response_model=UserResponse)
def me(token_payload: TokenPayload = Depends(get_current_token_payload), auth=Depends(get_auth_service)):
    """
    This returns the user identity embedded in the current bearer token.
    """

    user = auth.get_user_by_id(token_payload.sub)
    return UserResponse(**user)
