"""
File: service.py
Owner: BOTH CAN ADD
Created: 2026-03-21
Project: Learnova (eLearning Platform)
Purpose: Handle database-backed auth operations for the Learnova backend.
What it is: Service helpers for user registration, login, token generation, and DB health.
"""

from __future__ import annotations

import json
import os
from urllib import error, parse, request
from typing import Any

from fastapi import HTTPException, status

from backend.config.db import connect
from backend.config.security import create_access_token, hash_password, verify_password


def _row_to_dict(cursor, row) -> dict[str, Any] | None:
    """
    This keeps DB access compatible with both psycopg v3 and psycopg2 without custom row factories.
    """

    if row is None:
        return None

    column_names = [description[0] for description in cursor.description]
    return dict(zip(column_names, row))


def check_database_health() -> dict[str, Any]:
    """
    This runs a tiny query to confirm that the application can reach PostgreSQL.
    """

    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user;")
            current_database, current_user = cursor.fetchone()

    return {
        "status": "ok",
        "database": current_database,
        "user": current_user,
    }


def _count_users(cursor) -> int:
    cursor.execute("SELECT COUNT(*) FROM users;")
    return int(cursor.fetchone()[0])


def _serialize_user(user_row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(user_row["id"]),
        "name": user_row["name"],
        "email": user_row["email"],
        "role": user_row["role"],
        "provider": user_row["provider"],
        "is_active": bool(user_row["is_active"]),
    }


def _get_google_client_id() -> str:
    return os.getenv("GOOGLE_CLIENT_ID", os.getenv("VITE_GOOGLE_CLIENT_ID", "")).strip()


def _verify_google_credential(credential: str) -> dict[str, Any]:
    token_info_url = (
        "https://oauth2.googleapis.com/tokeninfo?"
        + parse.urlencode({"id_token": credential})
    )

    try:
        with request.urlopen(token_info_url, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google credential verification failed.",
        ) from exc
    except error.URLError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach Google for sign-in verification.",
        ) from exc

    expected_client_id = _get_google_client_id()
    audience = payload.get("aud", "")
    if expected_client_id and audience != expected_client_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google credential was issued for a different client application.",
        )

    if payload.get("email_verified") not in {"true", True}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google account email is not verified.",
        )

    if not payload.get("email") or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google profile payload is incomplete.",
        )

    return payload


def register_user(*, name: str, email: str, password: str, requested_role: str) -> dict[str, Any]:
    """
    This creates a new local-auth user in PostgreSQL and returns an auth response payload.
    """

    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE email = %s;", (email,))
            existing_user = cursor.fetchone()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already exists.",
                )

            role_to_store = "super_admin" if _count_users(cursor) == 0 else requested_role
            password_hash = hash_password(password)

            cursor.execute(
                """
                INSERT INTO users (name, email, password_hash, role, provider, is_active)
                VALUES (%s, %s, %s, %s, 'local', TRUE)
                RETURNING id, name, email, role, provider, is_active;
                """,
                (name, email, password_hash, role_to_store),
            )
            created_user = _row_to_dict(cursor, cursor.fetchone())
            connection.commit()

    serialized_user = _serialize_user(created_user)
    token = create_access_token(
        {
            "sub": serialized_user["id"],
            "email": serialized_user["email"],
            "role": serialized_user["role"],
        }
    )

    return {
        "access_token": token,
        "user": serialized_user,
    }


def check_email_availability(email: str) -> dict[str, Any]:
    """
    This checks whether a local or Google-backed account already exists for the email.
    """

    normalized_email = email.strip().lower()
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(%s);", (normalized_email,))
            existing_user = cursor.fetchone()

    return {
        "email": normalized_email,
        "isAvailable": existing_user is None,
        "message": "Email is available." if existing_user is None else "An account already exists for this email.",
    }


def login_user(*, email: str, password: str, requested_role: str) -> dict[str, Any]:
    """
    This verifies the local-auth credentials and returns a Bearer token response.
    """

    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, email, password_hash, role, provider, is_active
                FROM users
                WHERE email = %s;
                """,
                (email,),
            )
            user_row = _row_to_dict(cursor, cursor.fetchone())

    if not user_row or user_row["provider"] != "local":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(password, user_row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # A first-user bootstrap account is stored as super_admin but should still be allowed
    # through the admin-facing role path during login.
    effective_role = "admin" if user_row["role"] == "super_admin" else user_row["role"]
    if effective_role != requested_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Selected role does not match this account.",
        )

    serialized_user = _serialize_user(user_row)
    token = create_access_token(
        {
            "sub": serialized_user["id"],
            "email": serialized_user["email"],
            "role": serialized_user["role"],
        }
    )

    return {
        "access_token": token,
        "user": serialized_user,
    }


def login_with_google(*, credential: str, requested_role: str) -> dict[str, Any]:
    """
    This verifies the Google credential, then logs in or creates the matching user in PostgreSQL.
    """

    google_payload = _verify_google_credential(credential)
    normalized_email = google_payload["email"].strip().lower()

    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, email, role, provider, is_active, google_id
                FROM users
                WHERE LOWER(email) = LOWER(%s);
                """,
                (normalized_email,),
            )
            existing_user = _row_to_dict(cursor, cursor.fetchone())

            if existing_user:
                effective_role = "admin" if existing_user["role"] == "super_admin" else existing_user["role"]
                if effective_role != requested_role:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Selected role does not match this account.",
                    )

                if existing_user["provider"] == "local":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="This email is registered with password login. Use email and password instead.",
                    )

                cursor.execute(
                    """
                    UPDATE users
                    SET
                      name = %s,
                      google_id = %s,
                      provider = 'google',
                      updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, name, email, role, provider, is_active;
                    """,
                    (google_payload.get("name") or existing_user["name"], google_payload["sub"], existing_user["id"]),
                )
                user_row = _row_to_dict(cursor, cursor.fetchone())
            else:
                role_to_store = "super_admin" if _count_users(cursor) == 0 else requested_role
                cursor.execute(
                    """
                    INSERT INTO users (name, email, role, provider, google_id, is_active)
                    VALUES (%s, %s, %s, 'google', %s, TRUE)
                    RETURNING id, name, email, role, provider, is_active;
                    """,
                    (
                        google_payload.get("name") or normalized_email.split("@")[0],
                        normalized_email,
                        role_to_store,
                        google_payload["sub"],
                    ),
                )
                user_row = _row_to_dict(cursor, cursor.fetchone())

            connection.commit()

    serialized_user = _serialize_user(user_row)
    token = create_access_token(
        {
            "sub": serialized_user["id"],
            "email": serialized_user["email"],
            "role": serialized_user["role"],
        }
    )

    return {
        "access_token": token,
        "user": serialized_user,
    }


def get_user_by_id(user_id: str) -> dict[str, Any]:
    """
    This loads the current user from PostgreSQL so protected routes can return real account data.
    """

    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, email, role, provider, is_active
                FROM users
                WHERE id = %s;
                """,
                (user_id,),
            )
            user_row = _row_to_dict(cursor, cursor.fetchone())

    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return _serialize_user(user_row)
