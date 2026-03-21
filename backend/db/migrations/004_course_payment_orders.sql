-- File: 004_course_payment_orders.sql
-- Owner: BOTH CAN ADD
-- Purpose: Add persistent Razorpay order tracking for paid course enrollments.
-- What it is: A migration for storing order creation and verification state per learner and course.

BEGIN;

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

CREATE INDEX IF NOT EXISTS idx_course_payment_orders_user_id ON course_payment_orders(user_id);

COMMIT;
