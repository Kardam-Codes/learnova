"""
File: service.py
Owner: BOTH CAN ADD
Created: 2026-03-21
Project: Learnova (eLearning Platform)
Purpose: Handle database-backed auth operations for the Learnova backend.
What it is: Service helpers for user registration, login, token generation, and DB health.
"""

from __future__ import annotations

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
