"""
File: router.py
Owner: BOTH CAN ADD
Created: 2026-03-21
Project: Learnova (eLearning Platform)
Purpose: Expose learner-facing course read APIs backed by PostgreSQL.
What it is: FastAPI routes for course catalog, single course detail, and course reviews.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.modules.auth.dependencies import get_current_user
from backend.modules.courses.service import (
    create_course_payment_order,
    enroll_in_course,
    get_course_content_for_user,
    get_course_detail_for_user,
    get_course_reviews_for_user,
    get_quiz_for_user,
    list_courses_for_user,
    submit_course_review,
    submit_quiz_attempt,
    update_content_progress_for_user,
    verify_course_payment,
)
from backend.modules.courses.schemas import (
    ContentProgressUpdateRequest,
    PaymentVerificationRequest,
    QuizAttemptRequest,
    ReviewSubmissionRequest,
)


router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("")
def list_courses(current_user: dict = Depends(get_current_user)):
    """
    This returns the learner dashboard payload for the authenticated user.
    """

    return list_courses_for_user(current_user)


@router.post("/{course_slug}/enroll")
def post_course_enrollment(course_slug: str, current_user: dict = Depends(get_current_user)):
    """
    This enrolls the current learner in a free self-enrollable course.
    """

    return enroll_in_course(course_slug, current_user)


@router.get("/{course_slug}")
def get_course(course_slug: str, current_user: dict = Depends(get_current_user)):
    """
    This returns the learner-facing detail payload for one course.
    """

    return get_course_detail_for_user(course_slug, current_user)


@router.get("/{course_slug}/reviews")
def get_course_reviews(course_slug: str, current_user: dict = Depends(get_current_user)):
    """
    This returns the review payload for one course.
    """

    return get_course_reviews_for_user(course_slug, current_user)


@router.post("/{course_slug}/reviews")
def post_course_review(
    course_slug: str,
    payload: ReviewSubmissionRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    This creates or updates the current learner review for the target course.
    """

    return submit_course_review(course_slug, current_user, payload.rating, payload.comment)


@router.post("/{course_slug}/payments/order")
def post_payment_order(course_slug: str, current_user: dict = Depends(get_current_user)):
    """
    This creates a Razorpay order for a paid course enrollment.
    """

    return create_course_payment_order(course_slug, current_user)


@router.post("/{course_slug}/payments/verify")
def post_payment_verification(
    course_slug: str,
    payload: PaymentVerificationRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    This verifies the Razorpay signature and marks the course enrollment as paid.
    """

    return verify_course_payment(course_slug, current_user, payload.model_dump())


@router.get("/{course_slug}/content/{content_slug}")
def get_course_content(course_slug: str, content_slug: str, current_user: dict = Depends(get_current_user)):
    """
    This returns a single content item payload for direct lesson-player loading.
    """

    return get_course_content_for_user(course_slug, content_slug, current_user)


@router.post("/{course_slug}/content/{content_slug}/progress")
def post_course_content_progress(
    course_slug: str,
    content_slug: str,
    payload: ContentProgressUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    This updates lesson/document/video progress for the current learner.
    """

    return update_content_progress_for_user(
        course_slug,
        content_slug,
        current_user,
        status_value=payload.status,
        last_position=payload.lastPosition,
    )


@router.get("/{course_slug}/quizzes/{content_slug}")
def get_quiz(course_slug: str, content_slug: str, current_user: dict = Depends(get_current_user)):
    """
    This returns the quiz payload for the requested course content slug.
    """

    return get_quiz_for_user(course_slug, content_slug, current_user)


@router.post("/{course_slug}/quizzes/{content_slug}/attempts")
def post_quiz_attempt(
    course_slug: str,
    content_slug: str,
    payload: QuizAttemptRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    This scores and stores a learner quiz attempt.
    """

    answer_payload = [answer.model_dump() for answer in payload.answers]
    return submit_quiz_attempt(course_slug, content_slug, current_user, answer_payload)
