-- File: 003_learning_progress_and_reviews.sql
-- Owner: BOTH CAN ADD
-- Purpose: Create quiz, progress, points, reviews, and reporting-support tables.
-- What it is: The third migration in the PostgreSQL chain.

BEGIN;

CREATE TABLE IF NOT EXISTS quizzes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  content_id UUID NOT NULL UNIQUE REFERENCES course_content(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  max_attempts INTEGER NOT NULL DEFAULT 4,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT quizzes_attempts_positive_chk CHECK (max_attempts > 0)
);

CREATE TABLE IF NOT EXISTS quiz_questions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
  question_text TEXT NOT NULL,
  display_order INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (quiz_id, display_order),
  CONSTRAINT quiz_questions_order_positive_chk CHECK (display_order > 0)
);

CREATE TABLE IF NOT EXISTS quiz_options (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question_id UUID NOT NULL REFERENCES quiz_questions(id) ON DELETE CASCADE,
  option_text TEXT NOT NULL,
  is_correct BOOLEAN NOT NULL DEFAULT FALSE,
  display_order INTEGER NOT NULL,
  UNIQUE (question_id, display_order),
  CONSTRAINT quiz_options_order_positive_chk CHECK (display_order > 0)
);

CREATE TABLE IF NOT EXISTS quiz_reward_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
  attempt_number INTEGER NOT NULL,
  points_awarded INTEGER NOT NULL,
  UNIQUE (quiz_id, attempt_number),
  CONSTRAINT quiz_reward_attempt_positive_chk CHECK (attempt_number > 0),
  CONSTRAINT quiz_reward_points_nonnegative_chk CHECK (points_awarded >= 0)
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  attempt_number INTEGER NOT NULL,
  score NUMERIC(5, 2) NOT NULL DEFAULT 0,
  points_earned INTEGER NOT NULL DEFAULT 0,
  submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (quiz_id, user_id, attempt_number),
  CONSTRAINT quiz_attempts_number_positive_chk CHECK (attempt_number > 0),
  CONSTRAINT quiz_attempts_score_range_chk CHECK (score >= 0 AND score <= 100),
  CONSTRAINT quiz_attempts_points_nonnegative_chk CHECK (points_earned >= 0)
);

CREATE TABLE IF NOT EXISTS quiz_attempt_answers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  attempt_id UUID NOT NULL REFERENCES quiz_attempts(id) ON DELETE CASCADE,
  question_id UUID NOT NULL REFERENCES quiz_questions(id) ON DELETE CASCADE,
  selected_option_id UUID NOT NULL REFERENCES quiz_options(id) ON DELETE CASCADE,
  is_correct BOOLEAN NOT NULL DEFAULT FALSE,
  UNIQUE (attempt_id, question_id)
);

CREATE TABLE IF NOT EXISTS course_progress (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  completion_percentage NUMERIC(5, 2) NOT NULL DEFAULT 0,
  completed_count INTEGER NOT NULL DEFAULT 0,
  incomplete_count INTEGER NOT NULL DEFAULT 0,
  current_content_id UUID REFERENCES course_content(id) ON DELETE SET NULL,
  status course_progress_status NOT NULL DEFAULT 'yet_to_start',
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (course_id, user_id),
  CONSTRAINT course_progress_completion_range_chk CHECK (
    completion_percentage >= 0 AND completion_percentage <= 100
  ),
  CONSTRAINT course_progress_counts_nonnegative_chk CHECK (
    completed_count >= 0 AND incomplete_count >= 0
  )
);

CREATE TABLE IF NOT EXISTS content_progress (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content_id UUID NOT NULL REFERENCES course_content(id) ON DELETE CASCADE,
  course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status content_progress_status NOT NULL DEFAULT 'not_started',
  last_position INTEGER NOT NULL DEFAULT 0,
  completed_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (content_id, user_id),
  CONSTRAINT content_progress_last_position_nonnegative_chk CHECK (last_position >= 0)
);

CREATE TABLE IF NOT EXISTS learner_points (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  total_points INTEGER NOT NULL DEFAULT 0,
  current_badge badge_level NOT NULL DEFAULT 'Newbie',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT learner_points_nonnegative_chk CHECK (total_points >= 0)
);

CREATE TABLE IF NOT EXISTS point_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  course_id UUID REFERENCES courses(id) ON DELETE SET NULL,
  quiz_id UUID REFERENCES quizzes(id) ON DELETE SET NULL,
  points_delta INTEGER NOT NULL,
  reason TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS course_reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  rating INTEGER NOT NULL,
  comment TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (course_id, user_id),
  CONSTRAINT course_reviews_rating_range_chk CHECK (rating BETWEEN 1 AND 5)
);

CREATE INDEX IF NOT EXISTS idx_quiz_questions_quiz_id ON quiz_questions(quiz_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user_id ON quiz_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_course_progress_user_id ON course_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_content_progress_user_id ON content_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_course_reviews_course_id ON course_reviews(course_id);
CREATE INDEX IF NOT EXISTS idx_point_events_user_id ON point_events(user_id);

CREATE OR REPLACE VIEW reporting_course_progress AS
SELECT
  ROW_NUMBER() OVER (ORDER BY c.title, u.name) AS sr_no,
  c.id AS course_id,
  c.title AS course_name,
  u.id AS participant_id,
  u.name AS participant_name,
  ca.enrolled_at AS enrolled_date,
  cp.started_at AS start_date,
  cp.completion_percentage,
  cp.completed_at AS completed_date,
  cp.status,
  COALESCE(SUM(cp_item.last_position), 0) AS time_spent
FROM course_attendees ca
JOIN courses c ON c.id = ca.course_id
JOIN users u ON u.id = ca.user_id
LEFT JOIN course_progress cp
  ON cp.course_id = ca.course_id AND cp.user_id = ca.user_id
LEFT JOIN content_progress cp_item
  ON cp_item.course_id = ca.course_id AND cp_item.user_id = ca.user_id
GROUP BY
  c.id, c.title, u.id, u.name, ca.enrolled_at,
  cp.started_at, cp.completion_percentage, cp.completed_at, cp.status;

COMMIT;
