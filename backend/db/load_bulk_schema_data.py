"""
Generate and optionally insert a 200-row bulk dataset across the concrete Learnova tables.

This script follows the logical entities described in DB_SCHEMA.md and targets the
actual PostgreSQL tables defined in backend/db/schema.sql.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5


ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_PATH = ROOT_DIR / "backend" / "db" / "bulk_seed_200.sql"
PASSWORD_HASH = (
    "pbkdf2_sha256$600000$3b6b772bdfd7803725e19f6e2315940e$"
    "c65bd22fe46cc6af1b0b342e80e12456ab9384585ad7fe7b939c70c071d91d17"
)


@dataclass(frozen=True)
class UserRecord:
    id: str
    name: str
    email: str
    role: str


def make_id(label: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"learnova-bulk:{label}"))


def sql_text(value: str | None) -> str:
    if value is None:
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


def sql_bool(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def build_users(count: int) -> tuple[list[UserRecord], list[UserRecord], list[UserRecord]]:
    instructors: list[UserRecord] = []
    learners: list[UserRecord] = []
    admins: list[UserRecord] = []

    for index in range(1, count + 1):
        if index == 1:
            role = "super_admin"
            target = admins
        elif index <= 10:
            role = "admin"
            target = admins
        elif index <= 30:
            role = "instructor"
            target = instructors
        else:
            role = "learner"
            target = learners

        target.append(
            UserRecord(
                id=make_id(f"user:{index}"),
                name=f"Bulk User {index:03d}",
                email=f"bulk.user.{index:03d}@learnova.dev",
                role=role,
            )
        )

    return admins, instructors, learners


def build_sql(count: int) -> str:
    admins, instructors, learners = build_users(count)
    users = admins + instructors + learners
    admin_pool = admins or users[:1]
    instructor_pool = instructors or admin_pool

    statements: list[str] = [
        "-- Auto-generated bulk seed aligned with DB_SCHEMA.md",
        "BEGIN;",
    ]

    for user in users:
        statements.append(
            f"""
INSERT INTO users (id, name, email, password_hash, role, provider, is_active)
VALUES ({sql_text(user.id)}, {sql_text(user.name)}, {sql_text(user.email)}, {sql_text(PASSWORD_HASH)}, {sql_text(user.role)}, 'local', TRUE)
ON CONFLICT (id) DO UPDATE
SET
  name = EXCLUDED.name,
  email = EXCLUDED.email,
  password_hash = EXCLUDED.password_hash,
  role = EXCLUDED.role,
  provider = EXCLUDED.provider,
  is_active = EXCLUDED.is_active,
  updated_at = NOW();
""".strip()
        )

    for index in range(1, count + 1):
        tag_id = make_id(f"tag:{index}")
        tag_name = f"Bulk Tag {index:03d}"
        statements.append(
            f"""
INSERT INTO course_tags (id, name)
VALUES ({sql_text(tag_id)}, {sql_text(tag_name)})
ON CONFLICT (id) DO UPDATE
SET name = EXCLUDED.name;
""".strip()
        )

    for index in range(1, count + 1):
        course_id = make_id(f"course:{index}")
        slug = f"bulk-course-{index:03d}"
        title = f"Bulk Course {index:03d}"
        created_by = admin_pool[(index - 1) % len(admin_pool)].id
        responsible = instructor_pool[(index - 1) % len(instructor_pool)].id
        access_rule = "payment" if index % 3 == 0 else ("invitation" if index % 3 == 1 else "open")
        visibility = "signed_in" if index % 2 == 0 else "everyone"
        price = "499" if access_rule == "payment" else "0"
        statements.append(
            f"""
INSERT INTO courses (
  id, slug, title, short_description, description, thumbnail_url, cover_image_url,
  website_id, visibility, access_rule, price, is_published, created_by, responsible_user_id
)
VALUES (
  {sql_text(course_id)},
  {sql_text(slug)},
  {sql_text(title)},
  {sql_text(f"Short description for {title}.")},
  {sql_text(f"Detailed description for {title} generated for bulk schema coverage.")},
  {sql_text(f"https://picsum.photos/seed/{slug}/600/400")},
  {sql_text(f"https://picsum.photos/seed/{slug}-cover/1200/600")},
  {sql_text(f"website-{index:03d}")},
  {sql_text(visibility)},
  {sql_text(access_rule)},
  {price},
  TRUE,
  {sql_text(created_by)},
  {sql_text(responsible)}
)
ON CONFLICT (id) DO UPDATE
SET
  slug = EXCLUDED.slug,
  title = EXCLUDED.title,
  short_description = EXCLUDED.short_description,
  description = EXCLUDED.description,
  thumbnail_url = EXCLUDED.thumbnail_url,
  cover_image_url = EXCLUDED.cover_image_url,
  website_id = EXCLUDED.website_id,
  visibility = EXCLUDED.visibility,
  access_rule = EXCLUDED.access_rule,
  price = EXCLUDED.price,
  is_published = EXCLUDED.is_published,
  created_by = EXCLUDED.created_by,
  responsible_user_id = EXCLUDED.responsible_user_id,
  updated_at = NOW();
""".strip()
        )

        statements.append(
            f"""
INSERT INTO course_tag_map (id, course_id, tag_id)
VALUES ({sql_text(make_id(f"course_tag_map:{index}"))}, {sql_text(course_id)}, {sql_text(make_id(f"tag:{index}"))})
ON CONFLICT (course_id, tag_id) DO NOTHING;
""".strip()
        )

        participant = users[index - 1]
        payment_status = "paid" if access_rule == "payment" else "not_required"
        statements.append(
            f"""
INSERT INTO course_attendees (id, course_id, user_id, enrollment_source, payment_status)
VALUES ({sql_text(make_id(f"course_attendee:{index}"))}, {sql_text(course_id)}, {sql_text(participant.id)}, 'self', {sql_text(payment_status)})
ON CONFLICT (course_id, user_id) DO UPDATE
SET
  enrollment_source = EXCLUDED.enrollment_source,
  payment_status = EXCLUDED.payment_status;
""".strip()
        )

        content_id = make_id(f"course_content:{index}")
        content_slug = f"bulk-quiz-content-{index:03d}"
        statements.append(
            f"""
INSERT INTO course_content (
  id, course_id, slug, title, content_type, content_mode, description, content_url,
  allow_download, duration_label, display_order, responsible_user_id
)
VALUES (
  {sql_text(content_id)},
  {sql_text(course_id)},
  {sql_text(content_slug)},
  {sql_text(f"Bulk Quiz Content {index:03d}")},
  'quiz',
  'quiz',
  {sql_text(f"Quiz content for bulk course {index:03d}.")},
  NULL,
  FALSE,
  {sql_text("1 question")},
  1,
  {sql_text(responsible)}
)
ON CONFLICT (id) DO UPDATE
SET
  course_id = EXCLUDED.course_id,
  slug = EXCLUDED.slug,
  title = EXCLUDED.title,
  content_type = EXCLUDED.content_type,
  content_mode = EXCLUDED.content_mode,
  description = EXCLUDED.description,
  content_url = EXCLUDED.content_url,
  allow_download = EXCLUDED.allow_download,
  duration_label = EXCLUDED.duration_label,
  display_order = EXCLUDED.display_order,
  responsible_user_id = EXCLUDED.responsible_user_id,
  updated_at = NOW();
""".strip()
        )

        statements.append(
            f"""
INSERT INTO content_attachments (id, content_id, attachment_type, label, url)
VALUES (
  {sql_text(make_id(f"content_attachment:{index}"))},
  {sql_text(content_id)},
  'link',
  {sql_text(f"Bulk attachment {index:03d}")},
  {sql_text(f"https://example.com/bulk/{index:03d}")}
)
ON CONFLICT (id) DO NOTHING;
""".strip()
        )

        quiz_id = make_id(f"quiz:{index}")
        statements.append(
            f"""
INSERT INTO quizzes (id, course_id, content_id, title, max_attempts)
VALUES (
  {sql_text(quiz_id)},
  {sql_text(course_id)},
  {sql_text(content_id)},
  {sql_text(f"Bulk Quiz {index:03d}")},
  4
)
ON CONFLICT (id) DO UPDATE
SET
  course_id = EXCLUDED.course_id,
  content_id = EXCLUDED.content_id,
  title = EXCLUDED.title,
  max_attempts = EXCLUDED.max_attempts,
  updated_at = NOW();
""".strip()
        )

        question_id = make_id(f"quiz_question:{index}")
        option_id = make_id(f"quiz_option:{index}")
        attempt_id = make_id(f"quiz_attempt:{index}")
        points = 5 + (index % 16)
        badge = (
            "Master" if points >= 101 else
            "Expert" if points >= 81 else
            "Specialist" if points >= 61 else
            "Achiever" if points >= 41 else
            "Explorer" if points >= 21 else
            "Newbie"
        )

        statements.extend(
            [
                f"""
INSERT INTO quiz_questions (id, quiz_id, question_text, display_order)
VALUES ({sql_text(question_id)}, {sql_text(quiz_id)}, {sql_text(f"What is the key idea in bulk quiz {index:03d}?")}, 1)
ON CONFLICT (id) DO UPDATE
SET
  quiz_id = EXCLUDED.quiz_id,
  question_text = EXCLUDED.question_text,
  display_order = EXCLUDED.display_order,
  updated_at = NOW();
""".strip(),
                f"""
INSERT INTO quiz_options (id, question_id, option_text, is_correct, display_order)
VALUES ({sql_text(option_id)}, {sql_text(question_id)}, {sql_text("Bulk-generated correct answer")}, TRUE, 1)
ON CONFLICT (id) DO UPDATE
SET
  question_id = EXCLUDED.question_id,
  option_text = EXCLUDED.option_text,
  is_correct = EXCLUDED.is_correct,
  display_order = EXCLUDED.display_order;
""".strip(),
                f"""
INSERT INTO quiz_reward_rules (id, quiz_id, attempt_number, points_awarded)
VALUES ({sql_text(make_id(f"quiz_reward_rule:{index}"))}, {sql_text(quiz_id)}, 1, {points})
ON CONFLICT (quiz_id, attempt_number) DO UPDATE
SET points_awarded = EXCLUDED.points_awarded;
""".strip(),
                f"""
INSERT INTO quiz_attempts (id, quiz_id, user_id, attempt_number, score, points_earned)
VALUES ({sql_text(attempt_id)}, {sql_text(quiz_id)}, {sql_text(participant.id)}, 1, 100, {points})
ON CONFLICT (id) DO UPDATE
SET
  quiz_id = EXCLUDED.quiz_id,
  user_id = EXCLUDED.user_id,
  attempt_number = EXCLUDED.attempt_number,
  score = EXCLUDED.score,
  points_earned = EXCLUDED.points_earned;
""".strip(),
                f"""
INSERT INTO quiz_attempt_answers (id, attempt_id, question_id, selected_option_id, is_correct)
VALUES ({sql_text(make_id(f"quiz_attempt_answer:{index}"))}, {sql_text(attempt_id)}, {sql_text(question_id)}, {sql_text(option_id)}, TRUE)
ON CONFLICT (attempt_id, question_id) DO UPDATE
SET
  selected_option_id = EXCLUDED.selected_option_id,
  is_correct = EXCLUDED.is_correct;
""".strip(),
                f"""
INSERT INTO content_progress (id, content_id, course_id, user_id, status, last_position, completed_at)
VALUES ({sql_text(make_id(f"content_progress:{index}"))}, {sql_text(content_id)}, {sql_text(course_id)}, {sql_text(participant.id)}, 'completed', 100, NOW())
ON CONFLICT (content_id, user_id) DO UPDATE
SET
  status = EXCLUDED.status,
  last_position = EXCLUDED.last_position,
  completed_at = EXCLUDED.completed_at,
  updated_at = NOW();
""".strip(),
                f"""
INSERT INTO course_progress (
  id, course_id, user_id, completion_percentage, completed_count, incomplete_count,
  current_content_id, status, started_at, completed_at
)
VALUES (
  {sql_text(make_id(f"course_progress:{index}"))},
  {sql_text(course_id)},
  {sql_text(participant.id)},
  100,
  1,
  0,
  {sql_text(content_id)},
  'completed',
  NOW(),
  NOW()
)
ON CONFLICT (course_id, user_id) DO UPDATE
SET
  completion_percentage = EXCLUDED.completion_percentage,
  completed_count = EXCLUDED.completed_count,
  incomplete_count = EXCLUDED.incomplete_count,
  current_content_id = EXCLUDED.current_content_id,
  status = EXCLUDED.status,
  started_at = EXCLUDED.started_at,
  completed_at = EXCLUDED.completed_at,
  updated_at = NOW();
""".strip(),
                f"""
INSERT INTO learner_points (id, user_id, total_points, current_badge)
VALUES ({sql_text(make_id(f"learner_points:{index}"))}, {sql_text(participant.id)}, {points}, {sql_text(badge)})
ON CONFLICT (user_id) DO UPDATE
SET
  total_points = EXCLUDED.total_points,
  current_badge = EXCLUDED.current_badge,
  updated_at = NOW();
""".strip(),
                f"""
INSERT INTO point_events (id, user_id, course_id, quiz_id, points_delta, reason)
VALUES (
  {sql_text(make_id(f"point_event:{index}"))},
  {sql_text(participant.id)},
  {sql_text(course_id)},
  {sql_text(quiz_id)},
  {points},
  {sql_text(f"Bulk quiz attempt reward {index:03d}")}
)
ON CONFLICT (id) DO NOTHING;
""".strip(),
                f"""
INSERT INTO course_reviews (id, course_id, user_id, rating, comment)
VALUES (
  {sql_text(make_id(f"course_review:{index}"))},
  {sql_text(course_id)},
  {sql_text(participant.id)},
  {(index % 5) + 1},
  {sql_text(f"Bulk review for course {index:03d}.")}
)
ON CONFLICT (course_id, user_id) DO UPDATE
SET
  rating = EXCLUDED.rating,
  comment = EXCLUDED.comment,
  updated_at = NOW();
""".strip(),
            ]
        )

    statements.append("COMMIT;")
    return "\n\n".join(statements) + "\n"


def execute_sql(sql_text_payload: str) -> None:
    from backend.config.db import connect

    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql_text_payload)
        connection.commit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate and optionally execute Learnova bulk schema data.")
    parser.add_argument("--count", type=int, default=200, help="Number of rows to generate per concrete table family.")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="Where to write the generated SQL file.")
    parser.add_argument("--execute", action="store_true", help="Execute the generated SQL against the configured PostgreSQL database.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sql_payload = build_sql(args.count)
    args.output.write_text(sql_payload, encoding="utf-8")
    print(f"Wrote bulk seed SQL to {args.output}")

    if args.execute:
        execute_sql(sql_payload)
        print("Executed bulk seed SQL against the configured database.")


if __name__ == "__main__":
    main()
