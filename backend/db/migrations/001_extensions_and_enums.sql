-- File: 001_extensions_and_enums.sql
-- Owner: BOTH CAN ADD
-- Purpose: Initialize PostgreSQL extensions and enum types for Learnova.
-- What it is: The first migration in the PostgreSQL chain.

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

COMMIT;
