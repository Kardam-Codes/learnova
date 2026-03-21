"""
File: schemas.py
Owner: BOTH CAN ADD
Created: 2026-03-21
Project: Learnova (eLearning Platform)
Purpose: Define request and response schemas for the auth API.
What it is: Pydantic models for registration, login, tokens, and user payloads.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


AllowedSignupRole = Literal["learner", "instructor", "admin"]


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
    provider: str
    is_active: bool


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: AllowedSignupRole = "learner"

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        """
        This mirrors the frontend password rules so backend validation stays authoritative.
        """

        has_upper = any(character.isupper() for character in value)
        has_lower = any(character.islower() for character in value)
        has_special = any(not character.isalnum() for character in value)

        if not has_upper:
            raise ValueError("Password must contain at least one uppercase letter.")
        if not has_lower:
            raise ValueError("Password must contain at least one lowercase letter.")
        if not has_special:
            raise ValueError("Password must contain at least one special character.")

        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    role: AllowedSignupRole = "learner"


class TokenPayload(BaseModel):
    sub: str
    email: EmailStr
    role: str
