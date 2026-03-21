"""
File: router.py
Owner: BOTH CAN ADD
Created: 2026-03-21
Project: Learnova (eLearning Platform)
Purpose: Expose the initial auth and DB health API routes.
What it is: A FastAPI router for auth endpoints and basic backend connectivity checks.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.modules.auth.dependencies import get_current_token_payload
from backend.modules.auth.schemas import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    TokenPayload,
    UserResponse,
)
from backend.modules.auth.service import check_database_health, login_user, register_user
from backend.modules.auth.service import get_user_by_id


router = APIRouter(tags=["auth"])


@router.get("/db/health", tags=["system"])
def db_health():
    """
    This route confirms that PostgreSQL is reachable from the backend layer.
    """

    return check_database_health()


@router.post("/auth/register", response_model=AuthResponse)
def register(payload: RegisterRequest):
    """
    This creates a local user account and returns a bearer token for the new session.
    """

    return register_user(
        name=payload.name,
        email=payload.email,
        password=payload.password,
        requested_role=payload.role,
    )


@router.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    """
    This authenticates an existing local user against the PostgreSQL users table.
    """

    return login_user(
        email=payload.email,
        password=payload.password,
        requested_role=payload.role,
    )


@router.get("/auth/me", response_model=UserResponse)
def me(token_payload: TokenPayload = Depends(get_current_token_payload)):
    """
    This returns the user identity embedded in the current bearer token.
    """

    user = get_user_by_id(token_payload.sub)
    return UserResponse(**user)
