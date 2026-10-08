"""
File: schemas.py
Owner: BOTH CAN ADD
Created: 2026-03-21
Project: Learnova (eLearning Platform)
Purpose: Define request payloads for learner course interactions.
What it is: Pydantic models for review submission and quiz attempts.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field


class ReviewSubmissionRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=3, max_length=2000)


class QuizAnswerRequest(BaseModel):
    questionId: str
    selectedOptionIndexes: list[Annotated[int, Field(ge=0)]] = Field(min_length=1)


class QuizAttemptRequest(BaseModel):
    answers: list[QuizAnswerRequest]


class ContentProgressUpdateRequest(BaseModel):
    status: str = Field(pattern="^(not_started|in_progress|completed)$")
    lastPosition: int = Field(ge=0, default=0)


class PaymentVerificationRequest(BaseModel):
    razorpayOrderId: str = Field(min_length=3, max_length=255)
    razorpayPaymentId: str = Field(min_length=3, max_length=255)
    razorpaySignature: str = Field(min_length=3, max_length=255)
