"""
File: security.py
Owner: BOTH CAN ADD
Created: 2026-03-21
Project: Learnova (eLearning Platform)
Purpose: Provide shared password hashing and token helpers for backend auth.
What it is: A lightweight security utility built only on the Python standard library.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any


DEFAULT_TOKEN_TTL_SECONDS = 60 * 60 * 12


def _get_secret_key() -> str:
    """
    This reads a local secret from the environment and falls back to a dev-safe value.
    A stronger value should be set in production.
    """

    return os.getenv("JWT_SECRET", "learnova-dev-secret")


def _urlsafe_b64encode(raw_bytes: bytes) -> str:
    return base64.urlsafe_b64encode(raw_bytes).rstrip(b"=").decode("utf-8")


def _urlsafe_b64decode(raw_text: str) -> bytes:
    padding = "=" * (-len(raw_text) % 4)
    return base64.urlsafe_b64decode((raw_text + padding).encode("utf-8"))


def hash_password(password: str) -> str:
    """
    Passwords are hashed with PBKDF2 so we do not store plain-text credentials.
    The stored value includes the salt and iteration count for verification.
    """

    salt = secrets.token_hex(16)
    iterations = 600_000
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    """
    This checks a plain-text password against the stored PBKDF2 hash format.
    """

    try:
        algorithm, iterations_text, salt, digest = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False

        expected_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations_text),
        ).hex()
        return hmac.compare_digest(expected_digest, digest)
    except (ValueError, TypeError):
        return False


def create_access_token(payload: dict[str, Any], expires_in_seconds: int = DEFAULT_TOKEN_TTL_SECONDS) -> str:
    """
    This creates a compact HMAC-signed token in JWT format so the frontend can send
    a standard Bearer token while we keep dependencies minimal.
    """

    header = {
        "alg": "HS256",
        "typ": "JWT",
    }
    token_payload = {
        **payload,
        "exp": int(time.time()) + expires_in_seconds,
    }

    encoded_header = _urlsafe_b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _urlsafe_b64encode(json.dumps(token_payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = hmac.new(
        _get_secret_key().encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    encoded_signature = _urlsafe_b64encode(signature)
    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def decode_access_token(token: str) -> dict[str, Any]:
    """
    This validates the HMAC signature and expiration on an incoming Bearer token.
    """

    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
    except ValueError as exc:
        raise ValueError("Invalid token format.") from exc

    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    expected_signature = hmac.new(
        _get_secret_key().encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    supplied_signature = _urlsafe_b64decode(encoded_signature)

    if not hmac.compare_digest(expected_signature, supplied_signature):
        raise ValueError("Invalid token signature.")

    payload = json.loads(_urlsafe_b64decode(encoded_payload).decode("utf-8"))
    if int(payload.get("exp", 0)) < int(time.time()):
        raise ValueError("Token has expired.")

    return payload
