-- File: schema.sql
-- Owner: BOTH CAN ADD
-- Purpose: Define the initial PostgreSQL schema for Learnova.
-- What it is: The first concrete database DDL for auth, courses, content, quizzes, progress, points, reviews, and reporting support.

BEGIN;

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
    CREATE TYPE user_role AS ENUM ('super_admin', 'admin', 'instructor', 'learner');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'auth_provider') THEN
    CREATE TYPE auth_provider AS ENUM ('local', 'google');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'course_visibility') THEN
    CREATE TYPE course_visibility AS ENUM ('everyone', 'signed_in');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'course_access_rule') THEN
    CREATE TYPE course_access_rule AS ENUM ('open', 'invitation', 'payment');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'enrollment_source') THEN
    CREATE TYPE enrollment_source AS ENUM ('self', 'invited', 'admin_added');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'payment_status') THEN
    CREATE TYPE payment_status AS ENUM ('not_required', 'pending', 'paid');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'content_type') THEN
    CREATE TYPE content_type AS ENUM ('lesson', 'quiz');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'content_mode') THEN
    CREATE TYPE content_mode AS ENUM ('video', 'document', 'image', 'quiz');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'attachment_type') THEN
    CREATE TYPE attachment_type AS ENUM ('file', 'link');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'course_progress_status') THEN
    CREATE TYPE course_progress_status AS ENUM ('yet_to_start', 'in_progress', 'completed');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'content_progress_status') THEN
    CREATE TYPE content_progress_status AS ENUM ('not_started', 'in_progress', 'completed');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'badge_level') THEN
    CREATE TYPE badge_level AS ENUM ('Newbie', 'Explorer', 'Achiever', 'Specialist', 'Expert', 'Master');
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT,
  role user_role NOT NULL DEFAULT 'learner',
  provider auth_provider NOT NULL DEFAULT 'local',
  google_id TEXT UNIQUE,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT users_password_or_google_chk CHECK (
    (provider = 'local' AND password_hash IS NOT NULL) OR
    (provider = 'google' AND google_id IS NOT NULL)
  )
);

CREATE TABLE IF NOT EXISTS courses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  short_description TEXT NOT NULL,
  description TEXT,
  thumbnail_url TEXT,
  cover_image_url TEXT,
  website_id TEXT,
  visibility course_visibility NOT NULL DEFAULT 'everyone',
  access_rule course_access_rule NOT NULL DEFAULT 'open',
  price NUMERIC(10, 2) NOT NULL DEFAULT 0,
  is_published BOOLEAN NOT NULL DEFAULT FALSE,
  created_by UUID REFERENCES users(id) ON DELETE SET NULL,
  responsible_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT courses_price_nonnegative_chk CHECK (price >= 0),
  CONSTRAINT courses_payment_price_chk CHECK (
    (access_rule = 'payment' AND price > 0) OR
    (access_rule <> 'payment')
  )
);

CREATE TABLE IF NOT EXISTS course_tags (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS course_tag_map (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  tag_id UUID NOT NULL REFERENCES course_tags(id) ON DELETE CASCADE,
  UNIQUE (course_id, tag_id)
);

CREATE TABLE IF NOT EXISTS course_attendees (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  enrolled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  enrollment_source enrollment_source NOT NULL DEFAULT 'self',
  payment_status payment_status NOT NULL DEFAULT 'not_required',
  UNIQUE (course_id, user_id)
);

CREATE TABLE IF NOT EXISTS course_content (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  slug TEXT NOT NULL,
  title TEXT NOT NULL,
  content_type content_type NOT NULL DEFAULT 'lesson',
  content_mode content_mode NOT NULL,
  description TEXT,
  content_url TEXT,
  allow_download BOOLEAN NOT NULL DEFAULT FALSE,
  duration_label TEXT,
  display_order INTEGER NOT NULL,
  responsible_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (course_id, slug),
  UNIQUE (course_id, display_order),
  CONSTRAINT course_content_order_positive_chk CHECK (display_order > 0),
  CONSTRAINT course_content_quiz_mode_chk CHECK (
    (content_type = 'quiz' AND content_mode = 'quiz') OR
    (content_type = 'lesson' AND content_mode <> 'quiz')
  )
);

CREATE TABLE IF NOT EXISTS content_attachments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content_id UUID NOT NULL REFERENCES course_content(id) ON DELETE CASCADE,
  attachment_type attachment_type NOT NULL,
  label TEXT NOT NULL,
  url TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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
  UNIQUE (attempt_id, question_id, selected_option_id)
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

CREATE TABLE IF NOT EXISTS course_payment_orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider TEXT NOT NULL DEFAULT 'razorpay',
  provider_order_id TEXT NOT NULL UNIQUE,
  provider_payment_id TEXT UNIQUE,
  amount_paise INTEGER NOT NULL,
  currency TEXT NOT NULL DEFAULT 'INR',
  status TEXT NOT NULL DEFAULT 'created',
  receipt TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  verified_at TIMESTAMPTZ,
  CONSTRAINT course_payment_orders_amount_chk CHECK (amount_paise > 0),
  CONSTRAINT course_payment_orders_status_chk CHECK (status IN ('created', 'paid', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_courses_publish_visibility ON courses(is_published, visibility);
CREATE INDEX IF NOT EXISTS idx_course_attendees_user_id ON course_attendees(user_id);
CREATE INDEX IF NOT EXISTS idx_course_content_course_id ON course_content(course_id);
CREATE INDEX IF NOT EXISTS idx_quiz_questions_quiz_id ON quiz_questions(quiz_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user_id ON quiz_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_course_progress_user_id ON course_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_content_progress_user_id ON content_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_course_reviews_course_id ON course_reviews(course_id);
CREATE INDEX IF NOT EXISTS idx_point_events_user_id ON point_events(user_id);
CREATE INDEX IF NOT EXISTS idx_course_payment_orders_user_id ON course_payment_orders(user_id);

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
