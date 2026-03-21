"""
File: router.py
Owner: BOTH CAN ADD
Created: 2026-03-21
Project: Learnova (eLearning Platform)
Purpose: Expose instructor/admin APIs for course management and attendees.
What it is: FastAPI routes for course CRUD, publish toggles, and attendee invitations.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.modules.admin.schemas import (
    AddAttendeesRequest,
    AdminContentCreateRequest,
    AdminContentUpdateRequest,
    AdminQuizCreateRequest,
    AdminQuizUpdateRequest,
    CourseCreateRequest,
    CourseUpdateRequest,
    PublishCourseRequest,
)
from backend.modules.admin.service import (
    add_course_attendees,
    create_admin_course,
    create_course_content,
    create_course_quiz,
    delete_admin_course,
    delete_course_content,
    delete_quiz_detail,
    get_admin_course,
    get_content_detail,
    get_quiz_detail,
    list_admin_courses,
    list_course_content,
    list_course_attendees,
    list_course_quizzes,
    set_course_publish_state,
    update_course_content,
    update_quiz_detail,
    update_admin_course,
)
from backend.modules.auth.dependencies import require_roles


router = APIRouter(prefix="/admin", tags=["admin"])


AdminOrInstructor = require_roles("admin", "instructor")


@router.get("/courses")
def get_admin_courses(current_user: dict = Depends(AdminOrInstructor)):
    """
    This returns the instructor/admin course list for backoffice views.
    """

    return list_admin_courses(current_user)


@router.post("/courses")
def post_admin_course(
    payload: CourseCreateRequest,
    current_user: dict = Depends(AdminOrInstructor),
):
    """
    This creates a new course record and attaches its initial tags.
    """

    return create_admin_course(current_user, payload.model_dump())


@router.get("/courses/{course_slug}")
def get_admin_course_detail(
    course_slug: str,
    _current_user: dict = Depends(AdminOrInstructor),
):
    """
    This returns one course record for the instructor course form.
    """

    return get_admin_course(course_slug)


@router.put("/courses/{course_slug}")
def put_admin_course(
    course_slug: str,
    payload: CourseUpdateRequest,
    _current_user: dict = Depends(AdminOrInstructor),
):
    """
    This updates the editable course fields and course tags.
    """

    return update_admin_course(course_slug, payload.model_dump())


@router.delete("/courses/{course_slug}")
def delete_course(
    course_slug: str,
    _current_user: dict = Depends(AdminOrInstructor),
):
    """
    This deletes a course and its dependent rows through database cascades.
    """

    return delete_admin_course(course_slug)


@router.post("/courses/{course_slug}/publish")
def publish_course(
    course_slug: str,
    payload: PublishCourseRequest,
    _current_user: dict = Depends(AdminOrInstructor),
):
    """
    This toggles the publish state used by the website/app visibility flow.
    """

    return set_course_publish_state(course_slug, payload.isPublished)


@router.get("/courses/{course_slug}/attendees")
def get_attendees(
    course_slug: str,
    _current_user: dict = Depends(AdminOrInstructor),
):
    """
    This returns the attendee list for the selected course.
    """

    return list_course_attendees(course_slug)


@router.post("/courses/{course_slug}/attendees")
def post_attendees(
    course_slug: str,
    payload: AddAttendeesRequest,
    _current_user: dict = Depends(AdminOrInstructor),
):
    """
    This adds or updates attendee enrollments and supports invitation/admin-added flows.
    """

    attendee_payload = [attendee.model_dump() for attendee in payload.attendees]
    return add_course_attendees(course_slug, attendee_payload)


@router.get("/courses/{course_slug}/content")
def get_course_content_list(
    course_slug: str,
    _current_user: dict = Depends(AdminOrInstructor),
):
    """
    This returns the ordered course content list for the instructor content tab.
    """

    return list_course_content(course_slug)


@router.post("/courses/{course_slug}/content")
def post_course_content(
    course_slug: str,
    payload: AdminContentCreateRequest,
    _current_user: dict = Depends(AdminOrInstructor),
):
    """
    This creates a lesson/content item for the selected course.
    """

    return create_course_content(course_slug, payload.model_dump())


@router.get("/content/{content_slug}")
def get_content(
    content_slug: str,
    _current_user: dict = Depends(AdminOrInstructor),
):
    """
    This returns one content record for the content editor.
    """

    return get_content_detail(content_slug)


@router.put("/content/{content_slug}")
def put_content(
    content_slug: str,
    payload: AdminContentUpdateRequest,
    _current_user: dict = Depends(AdminOrInstructor),
):
    """
    This updates an existing lesson/content item.
    """

    return update_course_content(content_slug, payload.model_dump())


@router.delete("/content/{content_slug}")
def delete_content(
    content_slug: str,
    _current_user: dict = Depends(AdminOrInstructor),
):
    """
    This deletes a lesson/content item.
    """

    return delete_course_content(content_slug)


@router.get("/courses/{course_slug}/quizzes")
def get_quizzes(
    course_slug: str,
    _current_user: dict = Depends(AdminOrInstructor),
):
    """
    This returns the quiz list for the selected course.
    """

    return list_course_quizzes(course_slug)


@router.post("/courses/{course_slug}/quizzes")
def post_quiz(
    course_slug: str,
    payload: AdminQuizCreateRequest,
    _current_user: dict = Depends(AdminOrInstructor),
):
    """
    This creates a quiz content item and its builder data.
    """

    return create_course_quiz(course_slug, payload.model_dump())


@router.get("/quizzes/{quiz_id}")
def get_quiz(
    quiz_id: str,
    _current_user: dict = Depends(AdminOrInstructor),
):
    """
    This returns one quiz payload for the quiz builder.
    """

    return get_quiz_detail(quiz_id)


@router.put("/quizzes/{quiz_id}")
def put_quiz(
    quiz_id: str,
    payload: AdminQuizUpdateRequest,
    _current_user: dict = Depends(AdminOrInstructor),
):
    """
    This updates quiz questions, options, rewards, and course-content metadata.
    """

    return update_quiz_detail(quiz_id, payload.model_dump())


@router.delete("/quizzes/{quiz_id}")
def delete_quiz(
    quiz_id: str,
    _current_user: dict = Depends(AdminOrInstructor),
):
    """
    This deletes a quiz and its linked quiz-type content record.
    """

    return delete_quiz_detail(quiz_id)
