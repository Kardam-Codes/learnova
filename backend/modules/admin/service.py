"""
File: service.py
Owner: BOTH CAN ADD
Created: 2026-03-21
Project: Learnova (eLearning Platform)
Purpose: Handle instructor/admin course CRUD and attendee management.
What it is: PostgreSQL-backed service helpers for course administration APIs.
"""

from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4
from collections import defaultdict
from typing import Any

from fastapi import HTTPException, status

from backend.config.db import connect
from backend.config.security import hash_password

UPLOADS_ROOT = Path(__file__).resolve().parents[2] / "uploads"


def _fetch_rows(cursor, query: str, params: tuple = ()) -> list[dict[str, Any]]:
    cursor.execute(query, params)
    column_names = [description[0] for description in cursor.description]
    return [dict(zip(column_names, row)) for row in cursor.fetchall()]


def _fetch_one(cursor, query: str, params: tuple = ()) -> dict[str, Any] | None:
    rows = _fetch_rows(cursor, query, params)
    return rows[0] if rows else None


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")
    return slug or "course"


def _safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", filename).strip("-")
    return cleaned or "upload.bin"


def _parse_duration_to_minutes(duration_label: str | None) -> int:
    if not duration_label:
        return 0

    normalized = duration_label.strip().lower()
    match = re.search(r"(\d+)", normalized)
    if not match:
        return 0

    value = int(match.group(1))
    if "question" in normalized:
        return value * 2
    if "hour" in normalized:
        return value * 60
    return value


def _format_duration_label(total_minutes: int) -> str:
    if total_minutes <= 0:
        return "-"
    if total_minutes < 60:
        return f"{total_minutes} min"
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours}h {minutes:02d}m" if minutes else f"{hours}h"


def _ensure_unique_course_slug(cursor, base_slug: str, exclude_course_id: str | None = None) -> str:
    slug = base_slug
    counter = 2
    while True:
        if exclude_course_id:
            existing = _fetch_one(
                cursor,
                "SELECT id FROM courses WHERE slug = %s AND id <> %s::uuid;",
                (slug, exclude_course_id),
            )
        else:
            existing = _fetch_one(cursor, "SELECT id FROM courses WHERE slug = %s;", (slug,))

        if not existing:
            return slug

        slug = f"{base_slug}-{counter}"
        counter += 1


def _get_or_create_tag_id(cursor, tag_name: str) -> str:
    existing_tag = _fetch_one(
        cursor,
        "SELECT id FROM course_tags WHERE LOWER(name) = LOWER(%s);",
        (tag_name,),
    )
    if existing_tag:
        return str(existing_tag["id"])

    cursor.execute(
        """
        INSERT INTO course_tags (name)
        VALUES (%s)
        RETURNING id;
        """,
        (tag_name,),
    )
    return str(cursor.fetchone()[0])


def _sync_course_tags(cursor, course_id: str, tags: list[str]) -> None:
    cursor.execute("DELETE FROM course_tag_map WHERE course_id = %s::uuid;", (course_id,))

    for tag_name in [tag.strip() for tag in tags if tag.strip()]:
        tag_id = _get_or_create_tag_id(cursor, tag_name)
        cursor.execute(
            """
            INSERT INTO course_tag_map (course_id, tag_id)
            VALUES (%s::uuid, %s::uuid)
            ON CONFLICT (course_id, tag_id) DO NOTHING;
            """,
        (course_id, tag_id),
        )


def _ensure_unique_content_slug(cursor, course_id: str, base_slug: str, exclude_content_id: str | None = None) -> str:
    slug = base_slug
    counter = 2
    while True:
        if exclude_content_id:
            existing = _fetch_one(
                cursor,
                "SELECT id FROM course_content WHERE course_id = %s::uuid AND slug = %s AND id <> %s::uuid;",
                (course_id, slug, exclude_content_id),
            )
        else:
            existing = _fetch_one(
                cursor,
                "SELECT id FROM course_content WHERE course_id = %s::uuid AND slug = %s;",
                (course_id, slug),
            )
        if not existing:
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


def _get_next_content_order(cursor, course_id: str) -> int:
    row = _fetch_one(
        cursor,
        "SELECT COALESCE(MAX(display_order), 0) AS max_order FROM course_content WHERE course_id = %s::uuid;",
        (course_id,),
    )
    return int(row["max_order"]) + 1


def _serialize_content(cursor, content_slug: str) -> dict[str, Any]:
    content_row = _fetch_one(
        cursor,
        """
        SELECT
          cc.id,
          cc.course_id,
          c.slug AS course_slug,
          cc.slug,
          cc.title,
          cc.content_type,
          cc.content_mode,
          cc.description,
          cc.content_url,
          cc.allow_download,
          cc.duration_label,
          cc.display_order,
          cc.responsible_user_id,
          responsible.name AS responsible_name
        FROM course_content cc
        JOIN courses c ON c.id = cc.course_id
        LEFT JOIN users responsible ON responsible.id = cc.responsible_user_id
        WHERE cc.slug = %s;
        """,
        (content_slug,),
    )
    if not content_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found.")

    attachment_rows = _fetch_rows(
        cursor,
        """
        SELECT id, label, url, attachment_type
        FROM content_attachments
        WHERE content_id = %s::uuid
        ORDER BY created_at ASC;
        """,
        (content_row["id"],),
    )

    return {
        "id": str(content_row["id"]),
        "courseSlug": content_row["course_slug"],
        "slug": content_row["slug"],
        "title": content_row["title"],
        "contentType": content_row["content_type"],
        "contentMode": content_row["content_mode"],
        "description": content_row["description"],
        "contentUrl": content_row["content_url"],
        "allowDownload": bool(content_row["allow_download"]),
        "durationLabel": content_row["duration_label"],
        "displayOrder": int(content_row["display_order"]),
        "responsibleUserId": str(content_row["responsible_user_id"]) if content_row["responsible_user_id"] else None,
        "responsibleName": content_row["responsible_name"],
        "attachments": [
            {
                "id": str(row["id"]),
                "label": row["label"],
                "url": row["url"],
                "attachmentType": row["attachment_type"],
            }
            for row in attachment_rows
        ],
    }


def _replace_content_attachments(cursor, content_id: str, attachments: list[dict[str, Any]]) -> None:
    cursor.execute("DELETE FROM content_attachments WHERE content_id = %s::uuid;", (content_id,))
    for attachment in attachments:
        cursor.execute(
            """
            INSERT INTO content_attachments (content_id, attachment_type, label, url)
            VALUES (%s::uuid, %s, %s, %s);
            """,
            (
                content_id,
                attachment["attachmentType"],
                attachment["label"],
                attachment["url"],
            ),
        )


def _serialize_quiz(cursor, quiz_id: str) -> dict[str, Any]:
    quiz_row = _fetch_one(
        cursor,
        """
        SELECT
          q.id,
          q.title,
          q.max_attempts,
          cc.slug AS content_slug,
          c.slug AS course_slug,
          cc.description,
          cc.duration_label
        FROM quizzes q
        JOIN course_content cc ON cc.id = q.content_id
        JOIN courses c ON c.id = q.course_id
        WHERE q.id = %s::uuid;
        """,
        (quiz_id,),
    )
    if not quiz_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")

    question_rows = _fetch_rows(
        cursor,
        """
        SELECT
          qq.id AS question_id,
          qq.question_text,
          qq.display_order AS question_order,
          qo.id AS option_id,
          qo.option_text,
          qo.is_correct,
          qo.display_order AS option_order
        FROM quiz_questions qq
        JOIN quiz_options qo ON qo.question_id = qq.id
        WHERE qq.quiz_id = %s::uuid
        ORDER BY qq.display_order, qo.display_order;
        """,
        (quiz_id,),
    )

    rewards = _fetch_rows(
        cursor,
        """
        SELECT attempt_number, points_awarded
        FROM quiz_reward_rules
        WHERE quiz_id = %s::uuid
        ORDER BY attempt_number ASC;
        """,
        (quiz_id,),
    )

    questions_by_id: dict[str, dict[str, Any]] = {}
    ordered_questions: list[dict[str, Any]] = []
    for row in question_rows:
        question_id = str(row["question_id"])
        if question_id not in questions_by_id:
            question_payload = {
                "id": question_id,
                "prompt": row["question_text"],
                "choices": [],
            }
            questions_by_id[question_id] = question_payload
            ordered_questions.append(question_payload)

        questions_by_id[question_id]["choices"].append(
            {
                "id": str(row["option_id"]),
                "label": row["option_text"],
                "isCorrect": bool(row["is_correct"]),
            }
        )

    reward_map = {int(row["attempt_number"]): int(row["points_awarded"]) for row in rewards}

    return {
        "id": str(quiz_row["id"]),
        "title": quiz_row["title"],
        "courseSlug": quiz_row["course_slug"],
        "contentSlug": quiz_row["content_slug"],
        "description": quiz_row["description"] or "",
        "durationLabel": quiz_row["duration_label"] or "",
        "maxAttempts": int(quiz_row["max_attempts"]),
        "questions": ordered_questions,
        "rewards": {
            "first": reward_map.get(1, 0),
            "second": reward_map.get(2, 0),
            "third": reward_map.get(3, 0),
            "fourthPlus": reward_map.get(4, 0),
        },
    }


def _serialize_course(cursor, course_slug: str) -> dict[str, Any]:
    course_row = _fetch_one(
        cursor,
        """
        SELECT
          c.id,
          c.slug,
          c.title,
          c.short_description,
          c.description,
          c.thumbnail_url,
          c.cover_image_url,
          c.website_id,
          c.visibility,
          c.access_rule,
          c.price,
          c.is_published,
          c.created_by,
          c.responsible_user_id,
          creator.name AS created_by_name,
          responsible.name AS responsible_name,
          COALESCE(attendee_stats.attendee_count, 0) AS attendee_count,
          COALESCE(content_stats.content_count, 0) AS content_count,
          COALESCE(content_stats.duration_minutes, 0) AS duration_minutes,
          COALESCE(view_stats.views_count, 0) AS views_count
        FROM courses c
        LEFT JOIN users creator ON creator.id = c.created_by
        LEFT JOIN users responsible ON responsible.id = c.responsible_user_id
        LEFT JOIN (
          SELECT course_id, COUNT(*) AS attendee_count
          FROM course_attendees
          GROUP BY course_id
        ) attendee_stats ON attendee_stats.course_id = c.id
        LEFT JOIN (
          SELECT
            course_id,
            COUNT(*) AS content_count,
            SUM(
              CASE
                WHEN duration_label ~* '[0-9]+' THEN
                  CASE
                    WHEN duration_label ILIKE '%question%' THEN CAST(regexp_replace(duration_label, '[^0-9]', '', 'g') AS INTEGER) * 2
                    WHEN duration_label ILIKE '%hour%' THEN CAST(regexp_replace(duration_label, '[^0-9]', '', 'g') AS INTEGER) * 60
                    ELSE CAST(regexp_replace(duration_label, '[^0-9]', '', 'g') AS INTEGER)
                  END
                ELSE 0
              END
            ) AS duration_minutes
          FROM course_content
          GROUP BY course_id
        ) content_stats ON content_stats.course_id = c.id
        LEFT JOIN (
          SELECT course_id, COUNT(*) AS views_count
          FROM course_progress
          WHERE status IN ('in_progress', 'completed')
          GROUP BY course_id
        ) view_stats ON view_stats.course_id = c.id
        WHERE c.slug = %s;
        """,
        (course_slug,),
    )
    if not course_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

    tag_rows = _fetch_rows(
        cursor,
        """
        SELECT t.name
        FROM course_tag_map ctm
        JOIN course_tags t ON t.id = ctm.tag_id
        WHERE ctm.course_id = %s::uuid
        ORDER BY t.name;
        """,
        (course_row["id"],),
    )

    return {
        "id": str(course_row["id"]),
        "slug": course_row["slug"],
        "title": course_row["title"],
        "shortDescription": course_row["short_description"],
        "description": course_row["description"],
        "thumbnailUrl": course_row["thumbnail_url"],
        "coverImageUrl": course_row["cover_image_url"],
        "websiteId": course_row["website_id"],
        "visibility": course_row["visibility"],
        "accessRule": course_row["access_rule"],
        "price": float(course_row["price"]),
        "isPublished": bool(course_row["is_published"]),
        "createdBy": str(course_row["created_by"]) if course_row["created_by"] else None,
        "createdByName": course_row["created_by_name"],
        "responsibleUserId": str(course_row["responsible_user_id"]) if course_row["responsible_user_id"] else None,
        "responsibleName": course_row["responsible_name"],
        "tags": [row["name"] for row in tag_rows],
        "attendeeCount": int(course_row["attendee_count"]),
        "contentCount": int(course_row["content_count"]),
        "durationMinutes": int(course_row["duration_minutes"] or 0),
        "durationLabel": _format_duration_label(int(course_row["duration_minutes"] or 0)),
        "viewsCount": int(course_row["views_count"] or 0),
    }


def list_admin_courses(_current_user: dict) -> dict[str, Any]:
    with connect() as connection:
        with connection.cursor() as cursor:
            course_rows = _fetch_rows(
                cursor,
                """
                SELECT slug
                FROM courses
                ORDER BY created_at DESC, title ASC;
                """,
            )
            courses = [_serialize_course(cursor, row["slug"]) for row in course_rows]

    return {"courses": courses}


def list_admin_users(roles: list[str] | None = None) -> dict[str, Any]:
    allowed_roles = {"super_admin", "admin", "instructor", "learner"}
    requested_roles = [role for role in (roles or ["super_admin", "admin", "instructor"]) if role in allowed_roles]
    if not requested_roles:
        requested_roles = ["super_admin", "admin", "instructor"]

    placeholders = ", ".join(["%s"] * len(requested_roles))

    with connect() as connection:
        with connection.cursor() as cursor:
            user_rows = _fetch_rows(
                cursor,
                f"""
                SELECT id, name, email, role, is_active
                FROM users
                WHERE role IN ({placeholders})
                ORDER BY
                  CASE role
                    WHEN 'super_admin' THEN 1
                    WHEN 'admin' THEN 2
                    WHEN 'instructor' THEN 3
                    ELSE 4
                  END,
                  name ASC;
                """,
                tuple(requested_roles),
            )

    return {
        "users": [
            {
                "id": str(row["id"]),
                "name": row["name"],
                "email": row["email"],
                "role": row["role"],
                "isActive": bool(row["is_active"]),
            }
            for row in user_rows
        ]
    }


def save_admin_upload(file_name: str, file_bytes: bytes, category: str, base_url: str) -> dict[str, Any]:
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    normalized_category = _slugify(category or "misc")
    target_dir = UPLOADS_ROOT / normalized_category
    target_dir.mkdir(parents=True, exist_ok=True)

    safe_name = _safe_filename(file_name)
    stored_name = f"{uuid4().hex}-{safe_name}"
    target_path = target_dir / stored_name
    target_path.write_bytes(file_bytes)

    relative_url = f"/uploads/{normalized_category}/{stored_name}"
    return {
        "fileName": safe_name,
        "storedName": stored_name,
        "category": normalized_category,
        "url": f"{base_url.rstrip('/')}{relative_url}",
        "relativeUrl": relative_url,
        "size": len(file_bytes),
    }


def get_admin_course(course_slug: str) -> dict[str, Any]:
    with connect() as connection:
        with connection.cursor() as cursor:
            return _serialize_course(cursor, course_slug)


def create_admin_course(current_user: dict, payload: dict[str, Any]) -> dict[str, Any]:
    with connect() as connection:
        with connection.cursor() as cursor:
            base_slug = _slugify(payload["title"])
            slug = _ensure_unique_course_slug(cursor, base_slug)

            cursor.execute(
                """
                INSERT INTO courses (
                  slug, title, short_description, description, thumbnail_url, cover_image_url,
                  website_id, visibility, access_rule, price, is_published, created_by, responsible_user_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::uuid, %s::uuid)
                RETURNING slug;
                """,
                (
                    slug,
                    payload["title"],
                    payload["shortDescription"],
                    payload.get("description"),
                    payload.get("thumbnailUrl"),
                    payload.get("coverImageUrl"),
                    payload.get("websiteId"),
                    payload["visibility"],
                    payload["accessRule"],
                    payload["price"],
                    payload.get("isPublished", False),
                    current_user["id"],
                    payload.get("responsibleUserId"),
                ),
            )
            created_slug = cursor.fetchone()[0]
            course_row = _fetch_one(cursor, "SELECT id FROM courses WHERE slug = %s;", (created_slug,))
            _sync_course_tags(cursor, str(course_row["id"]), payload.get("tags", []))
            connection.commit()
            return _serialize_course(cursor, created_slug)


def update_admin_course(course_slug: str, payload: dict[str, Any]) -> dict[str, Any]:
    with connect() as connection:
        with connection.cursor() as cursor:
            existing = _fetch_one(cursor, "SELECT id FROM courses WHERE slug = %s;", (course_slug,))
            if not existing:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

            next_slug = _ensure_unique_course_slug(cursor, _slugify(payload["title"]), str(existing["id"]))
            cursor.execute(
                """
                UPDATE courses
                SET
                  slug = %s,
                  title = %s,
                  short_description = %s,
                  description = %s,
                  thumbnail_url = %s,
                  cover_image_url = %s,
                  website_id = %s,
                  visibility = %s,
                  access_rule = %s,
                  price = %s,
                  is_published = %s,
                  responsible_user_id = %s::uuid,
                  updated_at = NOW()
                WHERE id = %s::uuid;
                """,
                (
                    next_slug,
                    payload["title"],
                    payload["shortDescription"],
                    payload.get("description"),
                    payload.get("thumbnailUrl"),
                    payload.get("coverImageUrl"),
                    payload.get("websiteId"),
                    payload["visibility"],
                    payload["accessRule"],
                    payload["price"],
                    payload.get("isPublished", False),
                    payload.get("responsibleUserId"),
                    str(existing["id"]),
                ),
            )
            _sync_course_tags(cursor, str(existing["id"]), payload.get("tags", []))
            connection.commit()
            return _serialize_course(cursor, next_slug)


def delete_admin_course(course_slug: str) -> dict[str, Any]:
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM courses WHERE slug = %s RETURNING slug;", (course_slug,))
            deleted = cursor.fetchone()
            if not deleted:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
            connection.commit()

    return {"deleted": True, "slug": deleted[0]}


def set_course_publish_state(course_slug: str, is_published: bool) -> dict[str, Any]:
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE courses
                SET is_published = %s, updated_at = NOW()
                WHERE slug = %s
                RETURNING slug;
                """,
                (is_published, course_slug),
            )
            updated = cursor.fetchone()
            if not updated:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
            connection.commit()
            return _serialize_course(cursor, updated[0])


def list_course_attendees(course_slug: str) -> dict[str, Any]:
    with connect() as connection:
        with connection.cursor() as cursor:
            course_row = _fetch_one(cursor, "SELECT id, slug FROM courses WHERE slug = %s;", (course_slug,))
            if not course_row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

            attendee_rows = _fetch_rows(
                cursor,
                """
                SELECT
                  ca.id,
                  u.id AS user_id,
                  u.name,
                  u.email,
                  u.role,
                  ca.enrolled_at,
                  ca.enrollment_source,
                  ca.payment_status
                FROM course_attendees ca
                JOIN users u ON u.id = ca.user_id
                WHERE ca.course_id = %s::uuid
                ORDER BY ca.enrolled_at DESC;
                """,
                (course_row["id"],),
            )

    return {
        "courseSlug": course_slug,
        "attendees": [
            {
                "id": str(row["id"]),
                "userId": str(row["user_id"]),
                "name": row["name"],
                "email": row["email"],
                "role": row["role"],
                "enrolledAt": row["enrolled_at"].isoformat() if row["enrolled_at"] else None,
                "enrollmentSource": row["enrollment_source"],
                "paymentStatus": row["payment_status"],
            }
            for row in attendee_rows
        ],
    }


def add_course_attendees(course_slug: str, attendees: list[dict[str, Any]]) -> dict[str, Any]:
    with connect() as connection:
        with connection.cursor() as cursor:
            course_row = _fetch_one(cursor, "SELECT id, slug FROM courses WHERE slug = %s;", (course_slug,))
            if not course_row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

            created_or_linked = []
            for attendee in attendees:
                user_row = _fetch_one(
                    cursor,
                    "SELECT id, name, email FROM users WHERE LOWER(email) = LOWER(%s);",
                    (attendee["email"],),
                )

                if not user_row:
                    temporary_password_hash = hash_password("Learnova@123")
                    cursor.execute(
                        """
                        INSERT INTO users (name, email, password_hash, role, provider, is_active)
                        VALUES (%s, %s, %s, 'learner', 'local', TRUE)
                        RETURNING id, name, email;
                        """,
                        (
                            attendee["name"],
                            attendee["email"],
                            temporary_password_hash,
                        ),
                    )
                    inserted = cursor.fetchone()
                    user_row = {
                        "id": inserted[0],
                        "name": inserted[1],
                        "email": inserted[2],
                    }

                cursor.execute(
                    """
                    INSERT INTO course_attendees (course_id, user_id, enrollment_source, payment_status)
                    VALUES (%s::uuid, %s::uuid, %s, %s)
                    ON CONFLICT (course_id, user_id)
                    DO UPDATE SET
                      enrollment_source = EXCLUDED.enrollment_source,
                      payment_status = EXCLUDED.payment_status;
                    """,
                    (
                        str(course_row["id"]),
                        str(user_row["id"]),
                        attendee["enrollmentSource"],
                        attendee["paymentStatus"],
                    ),
                )

                created_or_linked.append(
                    {
                        "userId": str(user_row["id"]),
                        "name": user_row["name"],
                        "email": user_row["email"],
                        "enrollmentSource": attendee["enrollmentSource"],
                        "paymentStatus": attendee["paymentStatus"],
                    }
                )

            connection.commit()

    return {
        "courseSlug": course_slug,
        "attendees": created_or_linked,
    }


def get_reporting_course_progress(status_filter: str | None = None) -> dict[str, Any]:
    allowed_statuses = {"yet_to_start", "in_progress", "completed"}
    normalized_filter = status_filter.lower() if status_filter else None
    if normalized_filter and normalized_filter not in allowed_statuses:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status filter.")

    with connect() as connection:
        with connection.cursor() as cursor:
            summary_row = _fetch_one(
                cursor,
                """
                SELECT
                  COUNT(*) AS total_participants,
                  COUNT(*) FILTER (WHERE status = 'yet_to_start') AS yet_to_start,
                  COUNT(*) FILTER (WHERE status = 'in_progress') AS in_progress,
                  COUNT(*) FILTER (WHERE status = 'completed') AS completed
                FROM reporting_course_progress;
                """,
            ) or {
                "total_participants": 0,
                "yet_to_start": 0,
                "in_progress": 0,
                "completed": 0,
            }

            if normalized_filter:
                row_query = """
                    SELECT *
                    FROM reporting_course_progress
                    WHERE status = %s
                    ORDER BY course_name, participant_name;
                """
                row_params = (normalized_filter,)
            else:
                row_query = """
                    SELECT *
                    FROM reporting_course_progress
                    ORDER BY course_name, participant_name;
                """
                row_params = ()

            row_payload = _fetch_rows(cursor, row_query, row_params)

    rows = []
    for index, row in enumerate(row_payload, start=1):
        time_spent_minutes = int(row["time_spent"] or 0)
        hours = time_spent_minutes // 60
        minutes = time_spent_minutes % 60
        rows.append(
            {
                "id": index,
                "courseId": str(row["course_id"]),
                "courseName": row["course_name"],
                "participantId": str(row["participant_id"]),
                "participantName": row["participant_name"],
                "enrolledDate": row["enrolled_date"].isoformat() if row["enrolled_date"] else None,
                "startDate": row["start_date"].isoformat() if row["start_date"] else None,
                "timeSpent": f"{hours}:{minutes:02d}",
                "completionPercentage": f"{float(row['completion_percentage'] or 0):.0f}%",
                "completedDate": row["completed_date"].isoformat() if row["completed_date"] else None,
                "status": row["status"] or "yet_to_start",
            }
        )

    summary = [
        {"id": "participants", "label": "Total Participants", "value": int(summary_row["total_participants"] or 0)},
        {"id": "yet-to-start", "label": "Yet to Start", "value": int(summary_row["yet_to_start"] or 0)},
        {"id": "in-progress", "label": "In Progress", "value": int(summary_row["in_progress"] or 0)},
        {"id": "completed", "label": "Completed", "value": int(summary_row["completed"] or 0)},
    ]

    return {
        "summary": summary,
        "rows": rows,
        "activeFilter": normalized_filter,
    }


def list_course_content(course_slug: str) -> dict[str, Any]:
    with connect() as connection:
        with connection.cursor() as cursor:
            course_row = _fetch_one(cursor, "SELECT id, slug FROM courses WHERE slug = %s;", (course_slug,))
            if not course_row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

            content_rows = _fetch_rows(
                cursor,
                """
                SELECT slug
                FROM course_content
                WHERE course_id = %s::uuid
                ORDER BY display_order ASC;
                """,
                (course_row["id"],),
            )
            contents = [_serialize_content(cursor, row["slug"]) for row in content_rows]

    return {"courseSlug": course_slug, "contentItems": contents}


def create_course_content(course_slug: str, payload: dict[str, Any]) -> dict[str, Any]:
    with connect() as connection:
        with connection.cursor() as cursor:
            course_row = _fetch_one(cursor, "SELECT id FROM courses WHERE slug = %s;", (course_slug,))
            if not course_row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

            base_slug = _slugify(payload["title"])
            slug = _ensure_unique_content_slug(cursor, str(course_row["id"]), base_slug)
            display_order = _get_next_content_order(cursor, str(course_row["id"]))
            cursor.execute(
                """
                INSERT INTO course_content (
                  course_id, slug, title, content_type, content_mode, description, content_url,
                  allow_download, duration_label, display_order, responsible_user_id
                )
                VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::uuid)
                RETURNING slug, id;
                """,
                (
                    str(course_row["id"]),
                    slug,
                    payload["title"],
                    payload["contentType"],
                    payload["contentMode"],
                    payload.get("description"),
                    payload.get("contentUrl"),
                    payload.get("allowDownload", False),
                    payload.get("durationLabel"),
                    display_order,
                    payload.get("responsibleUserId"),
                ),
            )
            created_slug, created_id = cursor.fetchone()
            _replace_content_attachments(cursor, str(created_id), payload.get("attachments", []))
            connection.commit()
            return _serialize_content(cursor, created_slug)


def get_content_detail(content_slug: str) -> dict[str, Any]:
    with connect() as connection:
        with connection.cursor() as cursor:
            return _serialize_content(cursor, content_slug)


def update_course_content(content_slug: str, payload: dict[str, Any]) -> dict[str, Any]:
    with connect() as connection:
        with connection.cursor() as cursor:
            existing = _fetch_one(
                cursor,
                "SELECT id, course_id FROM course_content WHERE slug = %s;",
                (content_slug,),
            )
            if not existing:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found.")

            next_slug = _ensure_unique_content_slug(
                cursor,
                str(existing["course_id"]),
                _slugify(payload["title"]),
                str(existing["id"]),
            )
            cursor.execute(
                """
                UPDATE course_content
                SET
                  slug = %s,
                  title = %s,
                  content_type = %s,
                  content_mode = %s,
                  description = %s,
                  content_url = %s,
                  allow_download = %s,
                  duration_label = %s,
                  responsible_user_id = %s::uuid,
                  updated_at = NOW()
                WHERE id = %s::uuid;
                """,
                (
                    next_slug,
                    payload["title"],
                    payload["contentType"],
                    payload["contentMode"],
                    payload.get("description"),
                    payload.get("contentUrl"),
                    payload.get("allowDownload", False),
                    payload.get("durationLabel"),
                    payload.get("responsibleUserId"),
                    str(existing["id"]),
                ),
            )
            _replace_content_attachments(cursor, str(existing["id"]), payload.get("attachments", []))
            connection.commit()
            return _serialize_content(cursor, next_slug)


def delete_course_content(content_slug: str) -> dict[str, Any]:
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM course_content WHERE slug = %s RETURNING slug;",
                (content_slug,),
            )
            deleted = cursor.fetchone()
            if not deleted:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found.")
            connection.commit()

    return {"deleted": True, "slug": deleted[0]}


def list_course_quizzes(course_slug: str) -> dict[str, Any]:
    with connect() as connection:
        with connection.cursor() as cursor:
            course_row = _fetch_one(cursor, "SELECT id FROM courses WHERE slug = %s;", (course_slug,))
            if not course_row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

            quiz_rows = _fetch_rows(
                cursor,
                """
                SELECT q.id
                FROM quizzes q
                WHERE q.course_id = %s::uuid
                ORDER BY q.created_at ASC;
                """,
                (course_row["id"],),
            )
            quizzes = [_serialize_quiz(cursor, str(row["id"])) for row in quiz_rows]

    return {"courseSlug": course_slug, "quizzes": quizzes}


def _replace_quiz_questions(cursor, quiz_id: str, questions: list[dict[str, Any]]) -> None:
    existing_questions = _fetch_rows(
        cursor,
        "SELECT id FROM quiz_questions WHERE quiz_id = %s::uuid;",
        (quiz_id,),
    )
    for row in existing_questions:
        cursor.execute("DELETE FROM quiz_options WHERE question_id = %s::uuid;", (row["id"],))
    cursor.execute("DELETE FROM quiz_questions WHERE quiz_id = %s::uuid;", (quiz_id,))

    for question_index, question in enumerate(questions, start=1):
        cursor.execute(
            """
            INSERT INTO quiz_questions (quiz_id, question_text, display_order)
            VALUES (%s::uuid, %s, %s)
            RETURNING id;
            """,
            (quiz_id, question["prompt"], question_index),
        )
        question_id = str(cursor.fetchone()[0])
        for option_index, choice in enumerate(question["choices"], start=1):
            cursor.execute(
                """
                INSERT INTO quiz_options (question_id, option_text, is_correct, display_order)
                VALUES (%s::uuid, %s, %s, %s);
                """,
                (
                    question_id,
                    choice["label"],
                    choice.get("isCorrect", False),
                    option_index,
                ),
            )


def _replace_quiz_rewards(cursor, quiz_id: str, rewards: dict[str, int]) -> None:
    cursor.execute("DELETE FROM quiz_reward_rules WHERE quiz_id = %s::uuid;", (quiz_id,))
    reward_values = [
        (1, rewards["first"]),
        (2, rewards["second"]),
        (3, rewards["third"]),
        (4, rewards["fourthPlus"]),
    ]
    for attempt_number, points_awarded in reward_values:
        cursor.execute(
            """
            INSERT INTO quiz_reward_rules (quiz_id, attempt_number, points_awarded)
            VALUES (%s::uuid, %s, %s);
            """,
            (quiz_id, attempt_number, points_awarded),
        )


def create_course_quiz(course_slug: str, payload: dict[str, Any]) -> dict[str, Any]:
    with connect() as connection:
        with connection.cursor() as cursor:
            course_row = _fetch_one(cursor, "SELECT id FROM courses WHERE slug = %s;", (course_slug,))
            if not course_row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

            content_payload = {
                "title": payload["title"],
                "contentType": "quiz",
                "contentMode": "quiz",
                "description": payload.get("description"),
                "contentUrl": None,
                "allowDownload": False,
                "durationLabel": payload.get("durationLabel"),
                "responsibleUserId": None,
                "attachments": [],
            }
            content = create_course_content(course_slug, content_payload)
            content_row = _fetch_one(cursor, "SELECT id FROM course_content WHERE slug = %s;", (content["slug"],))
            cursor.execute(
                """
                INSERT INTO quizzes (course_id, content_id, title, max_attempts)
                VALUES (%s::uuid, %s::uuid, %s, %s)
                RETURNING id;
                """,
                (
                    str(course_row["id"]),
                    str(content_row["id"]),
                    payload["title"],
                    payload["maxAttempts"],
                ),
            )
            quiz_id = str(cursor.fetchone()[0])
            _replace_quiz_questions(cursor, quiz_id, payload["questions"])
            _replace_quiz_rewards(cursor, quiz_id, payload["rewards"])
            connection.commit()
            return _serialize_quiz(cursor, quiz_id)


def get_quiz_detail(quiz_id: str) -> dict[str, Any]:
    with connect() as connection:
        with connection.cursor() as cursor:
            return _serialize_quiz(cursor, quiz_id)


def update_quiz_detail(quiz_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    with connect() as connection:
        with connection.cursor() as cursor:
            quiz_row = _fetch_one(
                cursor,
                "SELECT id, content_id FROM quizzes WHERE id = %s::uuid;",
                (quiz_id,),
            )
            if not quiz_row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")

            content_row = _fetch_one(
                cursor,
                "SELECT id, course_id FROM course_content WHERE id = %s::uuid;",
                (quiz_row["content_id"],),
            )
            next_content_slug = _ensure_unique_content_slug(
                cursor,
                str(content_row["course_id"]),
                _slugify(payload["title"]),
                str(content_row["id"]),
            )
            cursor.execute(
                """
                UPDATE course_content
                SET
                  slug = %s,
                  title = %s,
                  description = %s,
                  duration_label = %s,
                  updated_at = NOW()
                WHERE id = %s::uuid;
                """,
                (
                    next_content_slug,
                    payload["title"],
                    payload.get("description"),
                    payload.get("durationLabel"),
                    str(content_row["id"]),
                ),
            )
            cursor.execute(
                """
                UPDATE quizzes
                SET
                  title = %s,
                  max_attempts = %s,
                  updated_at = NOW()
                WHERE id = %s::uuid;
                """,
                (
                    payload["title"],
                    payload["maxAttempts"],
                    quiz_id,
                ),
            )
            _replace_quiz_questions(cursor, quiz_id, payload["questions"])
            _replace_quiz_rewards(cursor, quiz_id, payload["rewards"])
            connection.commit()
            return _serialize_quiz(cursor, quiz_id)


def delete_quiz_detail(quiz_id: str) -> dict[str, Any]:
    with connect() as connection:
        with connection.cursor() as cursor:
            quiz_row = _fetch_one(
                cursor,
                "SELECT id, content_id FROM quizzes WHERE id = %s::uuid;",
                (quiz_id,),
            )
            if not quiz_row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")

            cursor.execute("DELETE FROM quizzes WHERE id = %s::uuid;", (quiz_id,))
            cursor.execute("DELETE FROM course_content WHERE id = %s::uuid;", (quiz_row["content_id"],))
            connection.commit()

    return {"deleted": True, "id": quiz_id}
