"""
File: dependencies.py
Owner: BOTH CAN ADD
Created: 2026-03-21
Project: Learnova (eLearning Platform)
Purpose: Provide reusable auth dependencies for protected backend routes.
What it is: FastAPI dependencies that decode Bearer tokens and load the current user from PostgreSQL.
"""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from backend.config.security import decode_access_token
from backend.modules.auth.schemas import TokenPayload
from backend.modules.auth.service import get_user_by_id


def extract_bearer_token(authorization: str | None = Header(default=None)) -> str:
    """
    This extracts the Bearer token from the Authorization header for protected routes.
    """

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must use Bearer token format.",
        )

    return token


def get_current_token_payload(token: str = Depends(extract_bearer_token)) -> TokenPayload:
    """
    This verifies the signed token and converts it into the shared token payload schema.
    """

    try:
        decoded_payload = decode_access_token(token)
        return TokenPayload(**decoded_payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


def get_current_user(token_payload: TokenPayload = Depends(get_current_token_payload)) -> dict:
    """
    This loads the current authenticated user from PostgreSQL for downstream route logic.
    """

    return get_user_by_id(token_payload.sub)
