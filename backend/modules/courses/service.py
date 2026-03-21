"""
File: service.py
Owner: BOTH CAN ADD
Created: 2026-03-21
Project: Learnova (eLearning Platform)
Purpose: Build learner-facing course response payloads from PostgreSQL.
What it is: Query helpers for course catalog, course detail, and review data.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from backend.config.db import connect


BADGE_TIERS = [
    {"name": "Newbie", "minPoints": 0, "maxPoints": 20},
    {"name": "Explorer", "minPoints": 21, "maxPoints": 40},
    {"name": "Achiever", "minPoints": 41, "maxPoints": 60},
    {"name": "Specialist", "minPoints": 61, "maxPoints": 80},
    {"name": "Expert", "minPoints": 81, "maxPoints": 100},
    {"name": "Master", "minPoints": 101, "maxPoints": 120},
]


def _fetch_rows(cursor, query: str, params: tuple = ()) -> list[dict[str, Any]]:
    cursor.execute(query, params)
    column_names = [description[0] for description in cursor.description]
    return [dict(zip(column_names, row)) for row in cursor.fetchall()]


def _fetch_one(cursor, query: str, params: tuple = ()) -> dict[str, Any] | None:
    rows = _fetch_rows(cursor, query, params)
    return rows[0] if rows else None


def _get_profile(cursor, user_id: str, learner_name: str) -> dict[str, Any]:
    points_row = _fetch_one(
        cursor,
        """
        SELECT total_points, current_badge
        FROM learner_points
        WHERE user_id = %s;
        """,
        (user_id,),
    )
    return {
        "learnerName": learner_name,
        "totalPoints": int(points_row["total_points"]) if points_row else 0,
        "currentBadge": points_row["current_badge"] if points_row else "Newbie",
        "badgeTiers": BADGE_TIERS,
    }


def _load_tag_map(cursor) -> dict[str, list[str]]:
    tag_rows = _fetch_rows(
        cursor,
        """
        SELECT c.slug AS course_slug, t.name AS tag_name
        FROM courses c
        JOIN course_tag_map ctm ON ctm.course_id = c.id
        JOIN course_tags t ON t.id = ctm.tag_id
        ORDER BY c.slug, t.name;
        """,
    )
    grouped_tags: dict[str, list[str]] = defaultdict(list)
    for row in tag_rows:
        grouped_tags[row["course_slug"]].append(row["tag_name"])
    return grouped_tags


def _load_content_rows(cursor, course_id: str, user_id: str) -> list[dict[str, Any]]:
    return _fetch_rows(
        cursor,
        """
        SELECT
          cc.id,
          cc.slug,
          cc.title,
          cc.content_type,
          cc.content_mode,
          cc.description,
          cc.content_url,
          cc.allow_download,
          cc.duration_label,
          cc.display_order,
          cp.status,
          cp.completed_at
        FROM course_content cc
        LEFT JOIN content_progress cp
          ON cp.content_id = cc.id AND cp.user_id = %s
        WHERE cc.course_id = %s
        ORDER BY cc.display_order;
        """,
        (user_id, course_id),
    )


def _load_content_row_by_slug(cursor, course_slug: str, content_slug: str, user_id: str) -> dict[str, Any] | None:
    rows = _fetch_rows(
        cursor,
        """
        SELECT
          cc.id,
          cc.course_id,
          cc.slug,
          cc.title,
          cc.content_type,
          cc.content_mode,
          cc.description,
          cc.content_url,
          cc.allow_download,
          cc.duration_label,
          cc.display_order,
          cp.status,
          cp.completed_at
        FROM course_content cc
        JOIN courses c ON c.id = cc.course_id
        LEFT JOIN content_progress cp
          ON cp.content_id = cc.id AND cp.user_id = %s
        WHERE c.slug = %s AND cc.slug = %s;
        """,
        (user_id, course_slug, content_slug),
    )
    return rows[0] if rows else None


def _load_attachment_map(cursor, content_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    if not content_ids:
        return {}

    attachment_rows = _fetch_rows(
        cursor,
        """
        SELECT content_id, id, label, url
        FROM content_attachments
        WHERE content_id = ANY(%s::uuid[])
        ORDER BY created_at;
        """,
        (content_ids,),
    )
    grouped_attachments: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in attachment_rows:
        grouped_attachments[str(row["content_id"])].append(
            {
                "id": str(row["id"]),
                "label": row["label"],
                "url": row["url"],
            }
        )
    return grouped_attachments


def _load_quiz_map(cursor, content_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not content_ids:
        return {}

    quiz_rows = _fetch_rows(
        cursor,
        """
        SELECT q.id, q.content_id, q.max_attempts, qq.id AS question_id, qq.question_text,
               qq.display_order AS question_order, qo.option_text, qo.display_order AS option_order,
               qo.is_correct
        FROM quizzes q
        JOIN quiz_questions qq ON qq.quiz_id = q.id
        JOIN quiz_options qo ON qo.question_id = qq.id
        WHERE q.content_id = ANY(%s::uuid[])
        ORDER BY q.content_id, qq.display_order, qo.display_order;
        """,
        (content_ids,),
    )

    reward_rows = _fetch_rows(
        cursor,
        """
        SELECT q.content_id, qrr.points_awarded, qrr.attempt_number
        FROM quizzes q
        JOIN quiz_reward_rules qrr ON qrr.quiz_id = q.id
        WHERE q.content_id = ANY(%s::uuid[])
        ORDER BY q.content_id, qrr.attempt_number;
        """,
        (content_ids,),
    )

    quiz_map: dict[str, dict[str, Any]] = {}
    question_map: dict[tuple[str, str], dict[str, Any]] = {}

    for row in quiz_rows:
        content_id = str(row["content_id"])
        if content_id not in quiz_map:
            quiz_map[content_id] = {
                "quizQuestions": [],
                "quizRules": {
                    "totalQuestions": 0,
                    "maxAttempts": int(row["max_attempts"]),
                },
            }

        question_key = (content_id, str(row["question_id"]))
        if question_key not in question_map:
            question_payload = {
                "id": str(row["question_id"]),
                "prompt": row["question_text"],
                "options": [],
                "correctOptionIndex": 0,
            }
            question_map[question_key] = question_payload
            quiz_map[content_id]["quizQuestions"].append(question_payload)

        question_payload = question_map[question_key]
        question_payload["options"].append(row["option_text"])
        if row["is_correct"]:
            question_payload["correctOptionIndex"] = int(row["option_order"]) - 1

    for content_id, payload in quiz_map.items():
        payload["quizRules"]["totalQuestions"] = len(payload["quizQuestions"])

    for row in reward_rows:
        content_id = str(row["content_id"])
        if content_id not in quiz_map:
            continue
        current_reward = quiz_map[content_id].setdefault(
            "reward",
            {
                "pointsEarned": 0,
                "nextTarget": 100,
                "message": "Reach the next rank to gain more points.",
            },
        )
        if int(row["attempt_number"]) == 1:
            current_reward["pointsEarned"] = int(row["points_awarded"])

    return quiz_map


def _serialize_content_items(cursor, course_id: str, user_id: str) -> list[dict[str, Any]]:
    content_rows = _load_content_rows(cursor, course_id, user_id)
    content_ids = [str(row["id"]) for row in content_rows]
    attachment_map = _load_attachment_map(cursor, content_ids)
    quiz_map = _load_quiz_map(cursor, content_ids)

    content_items: list[dict[str, Any]] = []
    for index, row in enumerate(content_rows):
        content_id = str(row["id"])
        status = row["status"] or "not_started"
        next_content_slug = content_rows[index + 1]["slug"] if index + 1 < len(content_rows) else None
        item = {
            "id": row["slug"],
            "title": row["title"],
            "type": row["content_type"],
            "mode": row["content_mode"],
            "status": status,
            "order": int(row["display_order"]),
            "duration": row["duration_label"],
            "description": row["description"],
            "contentUrl": row["content_url"],
            "attachments": attachment_map.get(content_id, []),
            "nextContentId": next_content_slug,
        }
        item.update(quiz_map.get(content_id, {}))
        content_items.append(item)

    return content_items


def _serialize_single_content_item(cursor, course_slug: str, content_slug: str, user_id: str) -> dict[str, Any]:
    content_row = _load_content_row_by_slug(cursor, course_slug, content_slug, user_id)
    if not content_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found.",
        )

    content_id = str(content_row["id"])
    attachment_map = _load_attachment_map(cursor, [content_id])
    quiz_map = _load_quiz_map(cursor, [content_id])
    next_content_row = _fetch_one(
        cursor,
        """
        SELECT slug
        FROM course_content
        WHERE course_id = %s AND display_order > %s
        ORDER BY display_order ASC
        LIMIT 1;
        """,
        (content_row["course_id"], content_row["display_order"]),
    )

    payload = {
        "id": content_row["slug"],
        "title": content_row["title"],
        "type": content_row["content_type"],
        "mode": content_row["content_mode"],
        "status": content_row["status"] or "not_started",
        "order": int(content_row["display_order"]),
        "duration": content_row["duration_label"],
        "description": content_row["description"],
        "contentUrl": content_row["content_url"],
        "attachments": attachment_map.get(content_id, []),
        "nextContentId": next_content_row["slug"] if next_content_row else None,
    }
    payload.update(quiz_map.get(content_id, {}))
    return payload


def list_courses_for_user(user: dict[str, Any]) -> dict[str, Any]:
    """
    This returns the learner dashboard payload with course-card data and profile data.
    """

    with connect() as connection:
        with connection.cursor() as cursor:
            tag_map = _load_tag_map(cursor)
            course_rows = _fetch_rows(
                cursor,
                """
                SELECT
                  c.id,
                  c.slug,
                  c.title,
                  c.short_description,
                  c.thumbnail_url,
                  c.cover_image_url,
                  c.access_rule,
                  c.price,
                  ca.payment_status,
                  cp.status AS progress_status,
                  current_content.slug AS current_content_slug,
                  first_content.slug AS first_content_slug,
                  first_content.content_mode AS first_content_mode,
                  last_content.slug AS last_content_slug,
                  last_content.content_mode AS last_content_mode
                FROM courses c
                LEFT JOIN course_attendees ca
                  ON ca.course_id = c.id AND ca.user_id = %s::uuid
                LEFT JOIN course_progress cp
                  ON cp.course_id = c.id AND cp.user_id = %s::uuid
                LEFT JOIN course_content current_content
                  ON current_content.id = cp.current_content_id
                LEFT JOIN LATERAL (
                  SELECT slug, content_mode
                  FROM course_content
                  WHERE course_id = c.id
                  ORDER BY display_order ASC
                  LIMIT 1
                ) AS first_content ON TRUE
                LEFT JOIN LATERAL (
                  SELECT cc.slug, cc.content_mode
                  FROM course_content cc
                  LEFT JOIN content_progress cprog
                    ON cprog.content_id = cc.id AND cprog.user_id = %s::uuid
                  WHERE cc.course_id = c.id
                  ORDER BY
                    CASE WHEN cprog.status = 'in_progress' THEN 0 ELSE 1 END,
                    CASE WHEN cprog.status = 'completed' THEN 1 ELSE 0 END,
                    cc.display_order ASC
                  LIMIT 1
                ) AS last_content ON TRUE
                WHERE c.is_published = TRUE
                ORDER BY c.title;
                """,
                (user["id"], user["id"], user["id"]),
            )
            profile = _get_profile(cursor, user["id"], user["name"])

    courses = []
    for row in course_rows:
        is_paid = row["access_rule"] == "payment"
        payment_status = row["payment_status"] or ("not_required" if not is_paid else "pending")
        progress_status = row["progress_status"] or "yet_to_start"
        courses.append(
            {
                "id": row["slug"],
                "title": row["title"],
                "shortDescription": row["short_description"],
                "coverImage": row["thumbnail_url"] or row["cover_image_url"],
                "tags": tag_map.get(row["slug"], []),
                "isPaid": is_paid,
                "price": float(row["price"]) if row["price"] is not None else None,
                "isPurchased": payment_status in {"paid", "not_required"},
                "isLoggedIn": True,
                "hasStarted": progress_status != "yet_to_start",
                "isInProgress": progress_status == "in_progress",
                "detailPath": f"/courses/{row['slug']}",
                "firstContentId": row["first_content_slug"],
                "firstContentMode": row["first_content_mode"],
                "lastContentId": row["current_content_slug"] or row["last_content_slug"] or row["first_content_slug"],
                "lastContentMode": row["last_content_mode"] or row["first_content_mode"],
            }
        )

    return {
        "profile": profile,
        "courses": courses,
    }


def get_course_detail_for_user(course_slug: str, user: dict[str, Any]) -> dict[str, Any]:
    """
    This returns one course detail payload shaped for the learner overview and player screens.
    """

    with connect() as connection:
        with connection.cursor() as cursor:
            course_row = _fetch_one(
                cursor,
                """
                SELECT
                  c.id,
                  c.slug,
                  c.title,
                  c.short_description,
                  c.thumbnail_url,
                  c.cover_image_url,
                  u.name AS provider_name,
                  cp.completion_percentage,
                  cp.completed_count,
                  cp.incomplete_count
                FROM courses c
                LEFT JOIN users u ON u.id = c.responsible_user_id
                LEFT JOIN course_progress cp
                  ON cp.course_id = c.id AND cp.user_id = %s::uuid
                WHERE c.slug = %s AND c.is_published = TRUE;
                """,
                (user["id"], course_slug),
            )
            if not course_row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Course not found.",
                )

            content_items = _serialize_content_items(cursor, str(course_row["id"]), user["id"])
            reviews = get_course_reviews_for_user(course_slug, user, cursor=cursor)

    total_count = len(content_items)
    completed_count = int(course_row["completed_count"] or 0)
    completion_percentage = float(course_row["completion_percentage"] or 0)
    incomplete_count = int(course_row["incomplete_count"] or max(total_count - completed_count, 0))

    return {
        "id": course_row["slug"],
        "title": course_row["title"],
        "shortDescription": course_row["short_description"],
        "thumbnail": course_row["thumbnail_url"],
        "coverImage": course_row["cover_image_url"],
        "providerName": course_row["provider_name"] or "Learnova",
        "learnerName": user["name"],
        "progress": {
            "completionPercentage": completion_percentage,
            "totalCount": total_count,
            "completedCount": completed_count,
            "incompleteCount": incomplete_count,
        },
        "contentItems": content_items,
        "reviews": reviews,
    }


def get_course_reviews_for_user(course_slug: str, user: dict[str, Any], cursor=None) -> dict[str, Any]:
    """
    This returns the review tab payload for a course, including the current learner draft text.
    """

    owns_connection = cursor is None
    if owns_connection:
        connection = connect()
        cursor = connection.cursor()
    else:
        connection = None

    try:
        review_rows = _fetch_rows(
            cursor,
            """
            SELECT
              cr.id,
              cr.user_id,
              cr.rating,
              cr.comment,
              review_user.name AS author_name
            FROM course_reviews cr
            JOIN courses c ON c.id = cr.course_id
            JOIN users review_user ON review_user.id = cr.user_id
            WHERE c.slug = %s
            ORDER BY cr.created_at ASC;
            """,
            (course_slug,),
        )

        learner_review = next(
            (row for row in review_rows if str(row["user_id"]) == str(user["id"])),
            None,
        )
        average_rating = (
            round(sum(float(row["rating"]) for row in review_rows) / len(review_rows), 1)
            if review_rows
            else 0
        )

        return {
            "averageRating": average_rating,
            "totalReviews": len(review_rows),
            "items": [
                {
                    "id": str(row["id"]),
                    "authorName": row["author_name"],
                    "rating": int(row["rating"]),
                    "comment": row["comment"],
                }
                for row in review_rows
            ],
            "learnerDraft": learner_review["comment"] if learner_review else "",
        }
    finally:
        if owns_connection and connection is not None:
            cursor.close()
            connection.close()


def get_course_content_for_user(course_slug: str, content_slug: str, user: dict[str, Any]) -> dict[str, Any]:
    """
    This returns a single content payload for direct player loading and deep links.
    """

    with connect() as connection:
        with connection.cursor() as cursor:
            course_row = _fetch_one(
                cursor,
                """
                SELECT id, slug, title
                FROM courses
                WHERE slug = %s AND is_published = TRUE;
                """,
                (course_slug,),
            )
            if not course_row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Course not found.",
                )

            content_item = _serialize_single_content_item(cursor, course_slug, content_slug, user["id"])

    return {
        "courseId": course_row["slug"],
        "courseTitle": course_row["title"],
        "contentItem": content_item,
    }


def submit_course_review(course_slug: str, user: dict[str, Any], rating: int, comment: str) -> dict[str, Any]:
    """
    This upserts the learner review and returns the refreshed review summary.
    """

    with connect() as connection:
        with connection.cursor() as cursor:
            course_row = _fetch_one(
                cursor,
                "SELECT id FROM courses WHERE slug = %s AND is_published = TRUE;",
                (course_slug,),
            )
            if not course_row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Course not found.",
                )

            cursor.execute(
                """
                INSERT INTO course_reviews (course_id, user_id, rating, comment)
                VALUES (%s, %s::uuid, %s, %s)
                ON CONFLICT (course_id, user_id)
                DO UPDATE SET
                  rating = EXCLUDED.rating,
                  comment = EXCLUDED.comment,
                  updated_at = NOW();
                """,
                (course_row["id"], user["id"], rating, comment),
            )
            connection.commit()

            return get_course_reviews_for_user(course_slug, user, cursor=cursor)


def get_quiz_for_user(course_slug: str, content_slug: str, user: dict[str, Any]) -> dict[str, Any]:
    """
    This returns the quiz-specific content payload for the requested course content slug.
    """

    content_payload = get_course_content_for_user(course_slug, content_slug, user)
    if content_payload["contentItem"]["mode"] != "quiz":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested content is not a quiz.",
        )

    return content_payload


def submit_quiz_attempt(course_slug: str, content_slug: str, user: dict[str, Any], answers: list[dict[str, Any]]) -> dict[str, Any]:
    """
    This scores a quiz attempt, stores the answers, awards points, and updates learner progress.
    """

    with connect() as connection:
        with connection.cursor() as cursor:
            quiz_row = _fetch_one(
                cursor,
                """
                SELECT
                  q.id AS quiz_id,
                  q.max_attempts,
                  q.content_id,
                  c.id AS course_id
                FROM quizzes q
                JOIN courses c ON c.id = q.course_id
                JOIN course_content cc ON cc.id = q.content_id
                WHERE c.slug = %s AND cc.slug = %s;
                """,
                (course_slug, content_slug),
            )
            if not quiz_row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Quiz not found.",
                )

            question_rows = _fetch_rows(
                cursor,
                """
                SELECT
                  qq.id AS question_id,
                  qq.question_text,
                  qo.id AS option_id,
                  qo.display_order,
                  qo.is_correct
                FROM quiz_questions qq
                JOIN quiz_options qo ON qo.question_id = qq.id
                WHERE qq.quiz_id = %s
                ORDER BY qq.display_order, qo.display_order;
                """,
                (quiz_row["quiz_id"],),
            )

            options_by_question: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in question_rows:
                options_by_question[str(row["question_id"])].append(row)

            submitted_answer_map = {
                answer["questionId"]: int(answer["selectedOptionIndex"])
                for answer in answers
            }

            if len(submitted_answer_map) != len(options_by_question):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="All quiz questions must be answered.",
                )

            attempt_count_row = _fetch_one(
                cursor,
                """
                SELECT COUNT(*) AS attempt_count
                FROM quiz_attempts
                WHERE quiz_id = %s AND user_id = %s::uuid;
                """,
                (quiz_row["quiz_id"], user["id"]),
            )
            attempt_number = int(attempt_count_row["attempt_count"]) + 1
            if attempt_number > int(quiz_row["max_attempts"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Maximum quiz attempts reached.",
                )

            correct_answers = 0
            answer_records = []
            for question_id, option_rows in options_by_question.items():
                selected_index = submitted_answer_map.get(question_id)
                if selected_index is None or selected_index >= len(option_rows):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="One or more quiz answers are invalid.",
                    )

                selected_option = option_rows[selected_index]
                is_correct = bool(selected_option["is_correct"])
                if is_correct:
                    correct_answers += 1

                answer_records.append(
                    {
                        "question_id": question_id,
                        "selected_option_id": str(selected_option["option_id"]),
                        "is_correct": is_correct,
                    }
                )

            score = round((correct_answers / max(len(options_by_question), 1)) * 100, 2)
            reward_row = _fetch_one(
                cursor,
                """
                SELECT points_awarded
                FROM quiz_reward_rules
                WHERE quiz_id = %s AND attempt_number = %s;
                """,
                (quiz_row["quiz_id"], attempt_number),
            ) or _fetch_one(
                cursor,
                """
                SELECT points_awarded
                FROM quiz_reward_rules
                WHERE quiz_id = %s
                ORDER BY attempt_number DESC
                LIMIT 1;
                """,
                (quiz_row["quiz_id"],),
            )
            points_earned = int(reward_row["points_awarded"]) if reward_row else 0

            cursor.execute(
                """
                INSERT INTO quiz_attempts (quiz_id, user_id, attempt_number, score, points_earned)
                VALUES (%s, %s::uuid, %s, %s, %s)
                RETURNING id;
                """,
                (quiz_row["quiz_id"], user["id"], attempt_number, score, points_earned),
            )
            attempt_id = str(cursor.fetchone()[0])

            for answer_record in answer_records:
                cursor.execute(
                    """
                    INSERT INTO quiz_attempt_answers (attempt_id, question_id, selected_option_id, is_correct)
                    VALUES (%s::uuid, %s::uuid, %s::uuid, %s);
                    """,
                    (
                        attempt_id,
                        answer_record["question_id"],
                        answer_record["selected_option_id"],
                        answer_record["is_correct"],
                    ),
                )

            cursor.execute(
                """
                INSERT INTO content_progress (content_id, course_id, user_id, status, last_position, completed_at)
                VALUES (%s, %s, %s::uuid, 'completed', 100, NOW())
                ON CONFLICT (content_id, user_id)
                DO UPDATE SET
                  status = 'completed',
                  last_position = 100,
                  completed_at = NOW(),
                  updated_at = NOW();
                """,
                (quiz_row["content_id"], quiz_row["course_id"], user["id"]),
            )

            progress_rows = _fetch_rows(
                cursor,
                """
                SELECT status
                FROM content_progress
                WHERE course_id = %s AND user_id = %s::uuid;
                """,
                (quiz_row["course_id"], user["id"]),
            )
            total_content_row = _fetch_one(
                cursor,
                "SELECT COUNT(*) AS total_count FROM course_content WHERE course_id = %s;",
                (quiz_row["course_id"],),
            )
            total_count = int(total_content_row["total_count"])
            completed_count = sum(1 for row in progress_rows if row["status"] == "completed")
            in_progress_count = sum(1 for row in progress_rows if row["status"] == "in_progress")
            completion_percentage = round((completed_count / max(total_count, 1)) * 100, 2)
            overall_status = "completed" if completed_count == total_count else ("in_progress" if completed_count or in_progress_count else "yet_to_start")
            completed_at = datetime.now(timezone.utc) if overall_status == "completed" else None

            cursor.execute(
                """
                INSERT INTO course_progress (
                  course_id, user_id, completion_percentage, completed_count, incomplete_count, current_content_id, status, started_at, completed_at
                )
                VALUES (%s, %s::uuid, %s, %s, %s, %s, %s, NOW(), %s)
                ON CONFLICT (course_id, user_id)
                DO UPDATE SET
                  completion_percentage = EXCLUDED.completion_percentage,
                  completed_count = EXCLUDED.completed_count,
                  incomplete_count = EXCLUDED.incomplete_count,
                  current_content_id = EXCLUDED.current_content_id,
                  status = EXCLUDED.status,
                  completed_at = EXCLUDED.completed_at,
                  updated_at = NOW();
                """,
                (
                    quiz_row["course_id"],
                    user["id"],
                    completion_percentage,
                    completed_count,
                    max(total_count - completed_count, 0),
                    quiz_row["content_id"],
                    overall_status,
                    completed_at,
                ),
            )

            cursor.execute(
                """
                INSERT INTO learner_points (user_id, total_points, current_badge)
                VALUES (%s::uuid, %s, 'Newbie')
                ON CONFLICT (user_id)
                DO UPDATE SET
                  total_points = learner_points.total_points + EXCLUDED.total_points,
                  current_badge = CASE
                    WHEN learner_points.total_points + EXCLUDED.total_points >= 101 THEN 'Master'::badge_level
                    WHEN learner_points.total_points + EXCLUDED.total_points >= 81 THEN 'Expert'::badge_level
                    WHEN learner_points.total_points + EXCLUDED.total_points >= 61 THEN 'Specialist'::badge_level
                    WHEN learner_points.total_points + EXCLUDED.total_points >= 41 THEN 'Achiever'::badge_level
                    WHEN learner_points.total_points + EXCLUDED.total_points >= 21 THEN 'Explorer'::badge_level
                    ELSE 'Newbie'::badge_level
                  END,
                  updated_at = NOW()
                RETURNING total_points, current_badge;
                """,
                (user["id"], points_earned),
            )
            learner_points_row = _fetch_one(
                cursor,
                """
                SELECT total_points, current_badge
                FROM learner_points
                WHERE user_id = %s::uuid;
                """,
                (user["id"],),
            )

            cursor.execute(
                """
                INSERT INTO point_events (user_id, course_id, quiz_id, points_delta, reason)
                VALUES (%s::uuid, %s, %s, %s, %s);
                """,
                (
                    user["id"],
                    quiz_row["course_id"],
                    quiz_row["quiz_id"],
                    points_earned,
                    f"Quiz attempt {attempt_number} reward",
                ),
            )
            connection.commit()

    next_target = 100
    total_points = int(learner_points_row["total_points"]) if learner_points_row else points_earned

    return {
        "attemptNumber": attempt_number,
        "score": score,
        "pointsEarned": points_earned,
        "totalPoints": total_points,
        "currentBadge": learner_points_row["current_badge"] if learner_points_row else "Newbie",
        "nextTarget": next_target,
        "message": "Reach the next rank to gain more points.",
    }
