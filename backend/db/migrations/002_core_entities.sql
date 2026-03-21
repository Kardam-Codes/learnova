-- File: 002_core_entities.sql
-- Owner: BOTH CAN ADD
-- Purpose: Create the core auth, course, tag, attendee, and content tables.
-- What it is: The second migration in the PostgreSQL chain.

BEGIN;

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

CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_courses_publish_visibility ON courses(is_published, visibility);
CREATE INDEX IF NOT EXISTS idx_course_attendees_user_id ON course_attendees(user_id);
CREATE INDEX IF NOT EXISTS idx_course_content_course_id ON course_content(course_id);

COMMIT;
