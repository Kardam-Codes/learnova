# DB_SCHEMA.md

## Purpose
This document defines the **target database shape** for Learnova based on:
- the problem statement
- current learner frontend flows
- planned instructor/admin features

This is a logical schema guide, not a finalized migration file.

Concrete SQL version:
- `backend/db/schema.sql`
- `backend/db/seed.sql`
- `backend/db/migrations/001_extensions_and_enums.sql`
- `backend/db/migrations/002_core_entities.sql`
- `backend/db/migrations/003_learning_progress_and_reviews.sql`
- `backend/db/README.md`

---

## 1. users

Fields:
- `id`
- `name`
- `email`
- `password_hash`
- `role`
- `provider`
- `google_id`
- `is_active`
- `created_at`
- `updated_at`

Notes:
- `email` should be unique
- `role` may include `super_admin`, `admin`, `instructor`, `learner`
- `provider` may be `local` or `google`

---

## 2. courses

Fields:
- `id`
- `slug`
- `title`
- `short_description`
- `description`
- `thumbnail_url`
- `cover_image_url`
- `website_id`
- `visibility`
- `access_rule`
- `price`
- `is_published`
- `created_by`
- `responsible_user_id`
- `created_at`
- `updated_at`

Notes:
- `visibility`: `everyone | signed_in`
- `access_rule`: `open | invitation | payment`
- `slug` supports route-friendly learner URLs

---

## 3. course_tags

Fields:
- `id`
- `name`
- `created_at`

---

## 4. course_tag_map

Fields:
- `id`
- `course_id`
- `tag_id`

---

## 5. course_attendees

Fields:
- `id`
- `course_id`
- `user_id`
- `enrolled_at`
- `enrollment_source`
- `payment_status`

Notes:
- `enrollment_source`: `self`, `invited`, `admin_added`
- `payment_status`: `not_required`, `pending`, `paid`

---

## 6. course_content

Fields:
- `id`
- `course_id`
- `slug`
- `title`
- `content_type`
- `content_mode`
- `description`
- `content_url`
- `allow_download`
- `duration_label`
- `display_order`
- `responsible_user_id`
- `created_at`
- `updated_at`

Notes:
- `content_type`: `lesson | quiz`
- `content_mode`: `video | document | image | quiz`
- `slug` supports stable per-content learner routes

---

## 7. content_attachments

Fields:
- `id`
- `content_id`
- `attachment_type`
- `label`
- `url`
- `created_at`

Notes:
- `attachment_type`: `file | link`

---

## 8. quizzes

Fields:
- `id`
- `course_id`
- `content_id`
- `title`
- `max_attempts`
- `created_at`
- `updated_at`

Notes:
- A quiz should be linked to a course and to the corresponding content item

---

## 9. quiz_questions

Fields:
- `id`
- `quiz_id`
- `question_text`
- `display_order`
- `created_at`
- `updated_at`

---

## 10. quiz_options

Fields:
- `id`
- `question_id`
- `option_text`
- `is_correct`
- `display_order`

---

## 11. quiz_reward_rules

Fields:
- `id`
- `quiz_id`
- `attempt_number`
- `points_awarded`

Notes:
- Example:
  - attempt 1 -> 20 points
  - attempt 2 -> 15 points
  - attempt 3 -> 10 points
  - 4+ -> 5 points

---

## 12. quiz_attempts

Fields:
- `id`
- `quiz_id`
- `user_id`
- `attempt_number`
- `score`
- `points_earned`
- `submitted_at`

---

## 13. quiz_attempt_answers

Fields:
- `id`
- `attempt_id`
- `question_id`
- `selected_option_id`
- `is_correct`

---

## 14. course_progress

Fields:
- `id`
- `course_id`
- `user_id`
- `completion_percentage`
- `completed_count`
- `incomplete_count`
- `current_content_id`
- `status`
- `started_at`
- `completed_at`
- `updated_at`

Notes:
- `status`: `yet_to_start | in_progress | completed`

---

## 15. content_progress

Fields:
- `id`
- `content_id`
- `course_id`
- `user_id`
- `status`
- `last_position`
- `completed_at`
- `updated_at`

Notes:
- `status`: `not_started | in_progress | completed`

---

## 16. learner_points

Fields:
- `id`
- `user_id`
- `total_points`
- `current_badge`
- `updated_at`

Badge ladder:
- `Newbie`
- `Explorer`
- `Achiever`
- `Specialist`
- `Expert`
- `Master`

---

## 17. point_events

Fields:
- `id`
- `user_id`
- `course_id`
- `quiz_id`
- `points_delta`
- `reason`
- `created_at`

---

## 18. course_reviews

Fields:
- `id`
- `course_id`
- `user_id`
- `rating`
- `comment`
- `created_at`
- `updated_at`

---

## 19. reporting_view_requirements

Course-wise reporting should be able to produce:
- course name
- participant name
- enrolled date
- start date
- time spent
- completion percentage
- completed date
- status

This may be implemented through a query/view rather than a dedicated table.

---

## Relationships Summary

- one `user` can enroll in many `courses`
- one `course` has many `content` items
- one `course` has many `reviews`
- one `quiz` has many `questions`
- one `question` has many `options`
- one `user` has progress across many courses and content items
- one `user` has many quiz attempts
- one `user` accumulates many point events

---

## SQL Implementation

The first concrete database implementation now exists at:

```plaintext
backend/db/schema.sql
```

Current assumption:
- PostgreSQL

It includes:
- enum types
- table definitions
- primary keys
- foreign keys
- check constraints
- unique constraints
- indexes
- a reporting view for course-wise learner progress
- route-friendly slug support for courses and content

Seed/bootstrap support now exists in:

```plaintext
backend/db/seed.sql
backend/db/migrations/001_extensions_and_enums.sql
backend/db/migrations/002_core_entities.sql
backend/db/migrations/003_learning_progress_and_reviews.sql
backend/db/README.md
```
