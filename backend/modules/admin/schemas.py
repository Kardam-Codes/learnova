"""
File: schemas.py
Owner: BOTH CAN ADD
Created: 2026-03-21
Project: Learnova (eLearning Platform)
Purpose: Define request payloads for instructor/admin course and attendee APIs.
What it is: Pydantic models for course CRUD, publish toggles, and attendee invitations.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class CourseCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    shortDescription: str = Field(min_length=3, max_length=500)
    description: str = ""
    thumbnailUrl: str | None = None
    coverImageUrl: str | None = None
    websiteId: str | None = None
    visibility: str = Field(pattern="^(everyone|signed_in)$", default="everyone")
    accessRule: str = Field(pattern="^(open|invitation|payment)$", default="open")
    price: float = Field(ge=0, default=0)
    responsibleUserId: str | None = None
    tags: list[str] = []
    isPublished: bool = False


class CourseUpdateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    shortDescription: str = Field(min_length=3, max_length=500)
    description: str = ""
    thumbnailUrl: str | None = None
    coverImageUrl: str | None = None
    websiteId: str | None = None
    visibility: str = Field(pattern="^(everyone|signed_in)$")
    accessRule: str = Field(pattern="^(open|invitation|payment)$")
    price: float = Field(ge=0, default=0)
    responsibleUserId: str | None = None
    tags: list[str] = []
    isPublished: bool = False


class PublishCourseRequest(BaseModel):
    isPublished: bool


class AttendeeInviteItem(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    enrollmentSource: str = Field(pattern="^(invited|admin_added)$", default="invited")
    paymentStatus: str = Field(pattern="^(not_required|pending|paid)$", default="not_required")


class AddAttendeesRequest(BaseModel):
    attendees: list[AttendeeInviteItem]


class AdminContentAttachmentPayload(BaseModel):
    id: str | None = None
    label: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=3, max_length=1000)
    attachmentType: str = Field(pattern="^(file|link)$", default="file")


class AdminContentCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    contentType: str = Field(pattern="^(lesson|quiz)$", default="lesson")
    contentMode: str = Field(pattern="^(video|document|image|quiz)$")
    description: str = ""
    contentUrl: str | None = None
    allowDownload: bool = False
    durationLabel: str | None = None
    responsibleUserId: str | None = None
    attachments: list[AdminContentAttachmentPayload] = []


class AdminContentUpdateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    contentType: str = Field(pattern="^(lesson|quiz)$")
    contentMode: str = Field(pattern="^(video|document|image|quiz)$")
    description: str = ""
    contentUrl: str | None = None
    allowDownload: bool = False
    durationLabel: str | None = None
    responsibleUserId: str | None = None
    attachments: list[AdminContentAttachmentPayload] = []


class AdminQuizChoicePayload(BaseModel):
    id: str | None = None
    label: str = Field(min_length=1, max_length=500)
    isCorrect: bool = False


class AdminQuizQuestionPayload(BaseModel):
    id: str | None = None
    prompt: str = Field(min_length=3, max_length=2000)
    choices: list[AdminQuizChoicePayload]


class AdminQuizRewardsPayload(BaseModel):
    first: int = Field(ge=0)
    second: int = Field(ge=0)
    third: int = Field(ge=0)
    fourthPlus: int = Field(ge=0)


class AdminQuizCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = ""
    durationLabel: str = "3 questions"
    maxAttempts: int = Field(ge=1, default=4)
    questions: list[AdminQuizQuestionPayload]
    rewards: AdminQuizRewardsPayload


class AdminQuizUpdateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = ""
    durationLabel: str = "3 questions"
    maxAttempts: int = Field(ge=1)
    questions: list[AdminQuizQuestionPayload]
    rewards: AdminQuizRewardsPayload
