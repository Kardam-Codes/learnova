-- File: seed.sql
-- Owner: BOTH CAN ADD
-- Purpose: Seed Learnova with demo-ready PostgreSQL data.
-- What it is: Idempotent inserts for users, courses, content, quizzes, progress, points, and reviews that mirror the current learner frontend flows.

BEGIN;

INSERT INTO users (id, name, email, password_hash, role, provider, is_active)
VALUES
  ('11111111-1111-1111-1111-111111111111', 'Kardam', 'kardam@learnova.dev', 'pbkdf2_sha256$600000$3b6b772bdfd7803725e19f6e2315940e$c65bd22fe46cc6af1b0b342e80e12456ab9384585ad7fe7b939c70c071d91d17', 'learner', 'local', TRUE),
  ('22222222-2222-2222-2222-222222222222', 'Yug', 'yug@learnova.dev', 'pbkdf2_sha256$600000$3b6b772bdfd7803725e19f6e2315940e$c65bd22fe46cc6af1b0b342e80e12456ab9384585ad7fe7b939c70c071d91d17', 'instructor', 'local', TRUE),
  ('33333333-3333-3333-3333-333333333333', 'Learnova Admin', 'admin@learnova.dev', 'pbkdf2_sha256$600000$3b6b772bdfd7803725e19f6e2315940e$c65bd22fe46cc6af1b0b342e80e12456ab9384585ad7fe7b939c70c071d91d17', 'super_admin', 'local', TRUE),
  ('44444444-4444-4444-4444-444444444444', 'Aman Gupta', 'aman@learnova.dev', 'pbkdf2_sha256$600000$3b6b772bdfd7803725e19f6e2315940e$c65bd22fe46cc6af1b0b342e80e12456ab9384585ad7fe7b939c70c071d91d17', 'learner', 'local', TRUE)
ON CONFLICT (id) DO UPDATE
SET
  name = EXCLUDED.name,
  email = EXCLUDED.email,
  password_hash = EXCLUDED.password_hash,
  role = EXCLUDED.role,
  provider = EXCLUDED.provider,
  is_active = EXCLUDED.is_active,
  updated_at = NOW();

INSERT INTO course_tags (id, name)
VALUES
  ('90000000-0000-0000-0000-000000000001', 'CRM'),
  ('90000000-0000-0000-0000-000000000002', 'Automation'),
  ('90000000-0000-0000-0000-000000000003', 'Sales'),
  ('90000000-0000-0000-0000-000000000004', 'Workflow'),
  ('90000000-0000-0000-0000-000000000005', 'Advanced'),
  ('90000000-0000-0000-0000-000000000006', 'Analytics'),
  ('90000000-0000-0000-0000-000000000007', 'Reports'),
  ('90000000-0000-0000-0000-000000000008', 'Growth')
ON CONFLICT (id) DO UPDATE
SET name = EXCLUDED.name;

INSERT INTO courses (
  id, slug, title, short_description, description, thumbnail_url, cover_image_url,
  visibility, access_rule, price, is_published, created_by, responsible_user_id
)
VALUES
  (
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1',
    'odoo-crm',
    'Basics of Odoo CRM',
    'Learn how to structure pipelines, automate sales stages, and manage leads inside Odoo CRM.',
    'A practical introductory CRM course covering pipeline structure, follow-ups, and lead flow.',
    'https://images.unsplash.com/photo-1552664730-d307ca884978?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1600&q=80',
    'signed_in',
    'open',
    0,
    TRUE,
    '22222222-2222-2222-2222-222222222222',
    '22222222-2222-2222-2222-222222222222'
  ),
  (
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2',
    'lead-management',
    'Lead Management Essentials',
    'Create a repeatable inbound workflow and learn how to qualify leads faster.',
    'A learner-friendly course on qualification, handoff, and lead response discipline.',
    'https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1520607162513-77705c0f0d4a?auto=format&fit=crop&w=1600&q=80',
    'signed_in',
    'open',
    0,
    TRUE,
    '22222222-2222-2222-2222-222222222222',
    '22222222-2222-2222-2222-222222222222'
  ),
  (
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3',
    'crm-automation-pro',
    'CRM Automation Pro',
    'Design event-driven automations, smart triggers, and conversion-ready funnels.',
    'An advanced automation course focused on trigger design and funnel automation.',
    'https://images.unsplash.com/photo-1556740749-887f6717d7e4?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=1600&q=80',
    'signed_in',
    'payment',
    500,
    TRUE,
    '22222222-2222-2222-2222-222222222222',
    '22222222-2222-2222-2222-222222222222'
  ),
  (
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4',
    'crm-analytics',
    'CRM Analytics Playbook',
    'Use dashboards, reports, and weekly review rituals to improve team performance.',
    'A course on performance analytics, reporting habits, and CRM insight loops.',
    'https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1518186233392-c232efbf2373?auto=format&fit=crop&w=1600&q=80',
    'signed_in',
    'payment',
    799,
    TRUE,
    '22222222-2222-2222-2222-222222222222',
    '22222222-2222-2222-2222-222222222222'
  )
ON CONFLICT (id) DO UPDATE
SET
  slug = EXCLUDED.slug,
  title = EXCLUDED.title,
  short_description = EXCLUDED.short_description,
  description = EXCLUDED.description,
  thumbnail_url = EXCLUDED.thumbnail_url,
  cover_image_url = EXCLUDED.cover_image_url,
  visibility = EXCLUDED.visibility,
  access_rule = EXCLUDED.access_rule,
  price = EXCLUDED.price,
  is_published = EXCLUDED.is_published,
  created_by = EXCLUDED.created_by,
  responsible_user_id = EXCLUDED.responsible_user_id,
  updated_at = NOW();

INSERT INTO course_tag_map (id, course_id, tag_id)
VALUES
  ('91000000-0000-0000-0000-000000000001', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', '90000000-0000-0000-0000-000000000001'),
  ('91000000-0000-0000-0000-000000000002', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', '90000000-0000-0000-0000-000000000002'),
  ('91000000-0000-0000-0000-000000000003', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', '90000000-0000-0000-0000-000000000003'),
  ('91000000-0000-0000-0000-000000000004', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2', '90000000-0000-0000-0000-000000000001'),
  ('91000000-0000-0000-0000-000000000005', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2', '90000000-0000-0000-0000-000000000004'),
  ('91000000-0000-0000-0000-000000000006', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3', '90000000-0000-0000-0000-000000000002'),
  ('91000000-0000-0000-0000-000000000007', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3', '90000000-0000-0000-0000-000000000005'),
  ('91000000-0000-0000-0000-000000000008', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4', '90000000-0000-0000-0000-000000000006'),
  ('91000000-0000-0000-0000-000000000009', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4', '90000000-0000-0000-0000-000000000007'),
  ('91000000-0000-0000-0000-000000000010', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4', '90000000-0000-0000-0000-000000000008')
ON CONFLICT (course_id, tag_id) DO NOTHING;

INSERT INTO course_attendees (id, course_id, user_id, enrollment_source, payment_status)
VALUES
  ('92000000-0000-0000-0000-000000000001', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', '11111111-1111-1111-1111-111111111111', 'self', 'not_required'),
  ('92000000-0000-0000-0000-000000000002', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2', '11111111-1111-1111-1111-111111111111', 'self', 'not_required'),
  ('92000000-0000-0000-0000-000000000003', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3', '11111111-1111-1111-1111-111111111111', 'self', 'pending'),
  ('92000000-0000-0000-0000-000000000004', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4', '11111111-1111-1111-1111-111111111111', 'self', 'paid')
ON CONFLICT (course_id, user_id) DO UPDATE
SET
  enrollment_source = EXCLUDED.enrollment_source,
  payment_status = EXCLUDED.payment_status;

DELETE FROM course_content
WHERE id IN (
  'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb004',
  'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb008'
);

INSERT INTO course_content (
  id, course_id, slug, title, content_type, content_mode, description, content_url,
  allow_download, duration_label, display_order, responsible_user_id
)
VALUES
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb001', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', 'advanced-sales-automation', 'Advanced Sales & CRM Automation in Odoo', 'lesson', 'video', 'Watch how pipeline automation, activity suggestions, and sales team stages fit together inside Odoo CRM.', 'https://www.youtube.com/embed/dQw4w9WgXcQ', FALSE, '14 min', 1, '22222222-2222-2222-2222-222222222222'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb002', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', 'odoo-best-practices', 'Odoo CRM: Advanced Features & Best Practices', 'lesson', 'document', 'Read the best-practice checklist covering segmentation, tags, saved filters, and weekly pipeline hygiene.', '/docs/dummy.pdf', TRUE, '11 min', 2, '22222222-2222-2222-2222-222222222222'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb003', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', 'pipeline-quiz', 'Pipeline Configuration Quiz', 'quiz', 'quiz', 'Answer a quick quiz on stage automation, lead scoring, and follow-up discipline before unlocking the final content.', NULL, FALSE, '3 questions', 3, '22222222-2222-2222-2222-222222222222'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb005', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2', 'lead-funnel-foundations', 'Lead Funnel Foundations', 'lesson', 'video', 'A practical overview of qualification stages and healthy lead movement.', 'https://www.youtube.com/embed/ysz5S6PUM-U', FALSE, '12 min', 1, '22222222-2222-2222-2222-222222222222'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb006', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2', 'lead-scoring-framework', 'Lead Scoring Framework', 'lesson', 'document', 'Set up a lightweight lead scoring model for better handoff decisions.', '/docs/dummy.pdf', TRUE, '10 min', 2, '22222222-2222-2222-2222-222222222222'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb007', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2', 'lead-response-quiz', 'Lead Response Time Quiz', 'quiz', 'quiz', 'Check how quickly your playbook should respond to high-intent leads.', NULL, FALSE, '3 questions', 3, '22222222-2222-2222-2222-222222222222'),

  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb009', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3', 'automation-blueprints', 'Automation Blueprints', 'lesson', 'video', 'Map trigger-based automations for lead movement and nurturing.', 'https://www.youtube.com/embed/aqz-KE-bpKQ', FALSE, '16 min', 1, '22222222-2222-2222-2222-222222222222'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb010', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3', 'trigger-design', 'Trigger Design Patterns', 'lesson', 'document', 'Choose the right event model for workflows that scale.', '/docs/dummy.pdf', TRUE, '13 min', 2, '22222222-2222-2222-2222-222222222222'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb011', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3', 'automation-quiz', 'Automation Logic Quiz', 'quiz', 'quiz', 'Validate your understanding of trigger conditions and actions.', NULL, FALSE, '3 questions', 3, '22222222-2222-2222-2222-222222222222'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb012', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3', 'handover-automation', 'Sales Handover Automation', 'lesson', 'video', 'Automate the transition from qualified lead to deal owner.', 'https://www.youtube.com/embed/ScMzIvxBSi4', FALSE, '9 min', 4, '22222222-2222-2222-2222-222222222222'),

  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb013', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4', 'metrics-foundation', 'Metrics Foundation', 'lesson', 'video', 'Identify the metrics that actually change revenue performance.', 'https://www.youtube.com/embed/M7lc1UVf-VE', FALSE, '15 min', 1, '22222222-2222-2222-2222-222222222222'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb014', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4', 'pipeline-reporting', 'Pipeline Reporting', 'lesson', 'document', 'Build a weekly reporting rhythm around lead and deal health.', '/docs/dummy.pdf', TRUE, '12 min', 2, '22222222-2222-2222-2222-222222222222'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb015', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4', 'analytics-quiz', 'Analytics Interpretation Quiz', 'quiz', 'quiz', 'Test how well you can read dashboards and spot warning signs.', NULL, FALSE, '3 questions', 3, '22222222-2222-2222-2222-222222222222')
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

INSERT INTO content_attachments (id, content_id, attachment_type, label, url)
VALUES
  ('93000000-0000-0000-0000-000000000001', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb001', 'file', 'Sales blueprint PDF', 'https://example.com/sales-blueprint.pdf'),
  ('93000000-0000-0000-0000-000000000002', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb002', 'file', 'Best practice checklist', 'https://example.com/best-practice-checklist.pdf'),
  ('93000000-0000-0000-0000-000000000003', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb006', 'file', 'Lead scoring sheet', 'https://example.com/scoring.pdf'),
  ('93000000-0000-0000-0000-000000000004', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb006', 'file', 'Lead template pack', 'https://example.com/lead-templates.pdf')
ON CONFLICT (id) DO NOTHING;

INSERT INTO quizzes (id, course_id, content_id, title, max_attempts)
VALUES
  ('cccccccc-cccc-cccc-cccc-ccccccccc001', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb003', 'Pipeline Configuration Quiz', 4),
  ('cccccccc-cccc-cccc-cccc-ccccccccc002', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb007', 'Lead Response Time Quiz', 4),
  ('cccccccc-cccc-cccc-cccc-ccccccccc003', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb011', 'Automation Logic Quiz', 4),
  ('cccccccc-cccc-cccc-cccc-ccccccccc004', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb015', 'Analytics Interpretation Quiz', 4)
ON CONFLICT (id) DO UPDATE
SET
  course_id = EXCLUDED.course_id,
  content_id = EXCLUDED.content_id,
  title = EXCLUDED.title,
  max_attempts = EXCLUDED.max_attempts,
  updated_at = NOW();

INSERT INTO quiz_reward_rules (id, quiz_id, attempt_number, points_awarded)
VALUES
  ('94000000-0000-0000-0000-000000000001', 'cccccccc-cccc-cccc-cccc-ccccccccc001', 1, 20),
  ('94000000-0000-0000-0000-000000000002', 'cccccccc-cccc-cccc-cccc-ccccccccc001', 2, 15),
  ('94000000-0000-0000-0000-000000000003', 'cccccccc-cccc-cccc-cccc-ccccccccc001', 3, 10),
  ('94000000-0000-0000-0000-000000000004', 'cccccccc-cccc-cccc-cccc-ccccccccc001', 4, 5),
  ('94000000-0000-0000-0000-000000000005', 'cccccccc-cccc-cccc-cccc-ccccccccc002', 1, 15),
  ('94000000-0000-0000-0000-000000000006', 'cccccccc-cccc-cccc-cccc-ccccccccc002', 2, 10),
  ('94000000-0000-0000-0000-000000000007', 'cccccccc-cccc-cccc-cccc-ccccccccc002', 3, 8),
  ('94000000-0000-0000-0000-000000000008', 'cccccccc-cccc-cccc-cccc-ccccccccc002', 4, 5)
ON CONFLICT (quiz_id, attempt_number) DO UPDATE
SET points_awarded = EXCLUDED.points_awarded;

INSERT INTO quiz_questions (id, quiz_id, question_text, display_order)
VALUES
  ('95000000-0000-0000-0000-000000000001', 'cccccccc-cccc-cccc-cccc-ccccccccc001', 'Which automation best reduces follow-up delay for new qualified leads?', 1),
  ('95000000-0000-0000-0000-000000000002', 'cccccccc-cccc-cccc-cccc-ccccccccc001', 'Why should a team use lead stages consistently in Odoo CRM?', 2),
  ('95000000-0000-0000-0000-000000000003', 'cccccccc-cccc-cccc-cccc-ccccccccc001', 'Which practice usually improves lead prioritization?', 3)
ON CONFLICT (id) DO UPDATE
SET
  quiz_id = EXCLUDED.quiz_id,
  question_text = EXCLUDED.question_text,
  display_order = EXCLUDED.display_order,
  updated_at = NOW();

INSERT INTO quiz_options (id, question_id, option_text, is_correct, display_order)
VALUES
  ('96000000-0000-0000-0000-000000000001', '95000000-0000-0000-0000-000000000001', 'Manual daily tracking only', FALSE, 1),
  ('96000000-0000-0000-0000-000000000002', '95000000-0000-0000-0000-000000000001', 'Automatic activity assignment after qualification', TRUE, 2),
  ('96000000-0000-0000-0000-000000000003', '95000000-0000-0000-0000-000000000001', 'Removing lead stages completely', FALSE, 3),
  ('96000000-0000-0000-0000-000000000004', '95000000-0000-0000-0000-000000000002', 'To reduce reporting clarity', FALSE, 1),
  ('96000000-0000-0000-0000-000000000005', '95000000-0000-0000-0000-000000000002', 'To make dashboards and ownership less reliable', FALSE, 2),
  ('96000000-0000-0000-0000-000000000006', '95000000-0000-0000-0000-000000000002', 'To keep pipeline reporting and handoff behavior structured', TRUE, 3),
  ('96000000-0000-0000-0000-000000000007', '95000000-0000-0000-0000-000000000003', 'Lead scoring rules tied to intent signals', TRUE, 1),
  ('96000000-0000-0000-0000-000000000008', '95000000-0000-0000-0000-000000000003', 'Random assignment with no conditions', FALSE, 2),
  ('96000000-0000-0000-0000-000000000009', '95000000-0000-0000-0000-000000000003', 'Ignoring contact source data', FALSE, 3)
ON CONFLICT (id) DO UPDATE
SET
  question_id = EXCLUDED.question_id,
  option_text = EXCLUDED.option_text,
  is_correct = EXCLUDED.is_correct,
  display_order = EXCLUDED.display_order;

INSERT INTO course_progress (
  id, course_id, user_id, completion_percentage, completed_count, incomplete_count,
  current_content_id, status, started_at, completed_at
)
VALUES
  ('97000000-0000-0000-0000-000000000001', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', '11111111-1111-1111-1111-111111111111', 33.33, 1, 2, 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb001', 'in_progress', NOW() - INTERVAL '7 days', NULL),
  ('97000000-0000-0000-0000-000000000002', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2', '11111111-1111-1111-1111-111111111111', 0, 0, 3, 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb005', 'yet_to_start', NULL, NULL),
  ('97000000-0000-0000-0000-000000000003', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4', '11111111-1111-1111-1111-111111111111', 75, 3, 1, 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb014', 'in_progress', NOW() - INTERVAL '21 days', NULL)
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

INSERT INTO content_progress (
  id, content_id, course_id, user_id, status, last_position, completed_at
)
VALUES
  ('98000000-0000-0000-0000-000000000001', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb001', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', '11111111-1111-1111-1111-111111111111', 'in_progress', 540, NULL),
  ('98000000-0000-0000-0000-000000000002', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb002', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', '11111111-1111-1111-1111-111111111111', 'completed', 660, NOW() - INTERVAL '6 days'),
  ('98000000-0000-0000-0000-000000000003', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb013', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4', '11111111-1111-1111-1111-111111111111', 'completed', 900, NOW() - INTERVAL '16 days'),
  ('98000000-0000-0000-0000-000000000004', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb014', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4', '11111111-1111-1111-1111-111111111111', 'in_progress', 480, NULL)
ON CONFLICT (content_id, user_id) DO UPDATE
SET
  status = EXCLUDED.status,
  last_position = EXCLUDED.last_position,
  completed_at = EXCLUDED.completed_at,
  updated_at = NOW();

INSERT INTO learner_points (id, user_id, total_points, current_badge)
VALUES
  ('99000000-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 20, 'Newbie')
ON CONFLICT (user_id) DO UPDATE
SET
  total_points = EXCLUDED.total_points,
  current_badge = EXCLUDED.current_badge,
  updated_at = NOW();

INSERT INTO point_events (id, user_id, course_id, quiz_id, points_delta, reason)
VALUES
  ('99100000-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', 'cccccccc-cccc-cccc-cccc-ccccccccc001', 20, 'First quiz completion reward')
ON CONFLICT (id) DO NOTHING;

INSERT INTO course_reviews (id, course_id, user_id, rating, comment)
VALUES
  ('99200000-0000-0000-0000-000000000001', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', '11111111-1111-1111-1111-111111111111', 5, 'Clear explanations and a very practical walkthrough of stage automation.'),
  ('99200000-0000-0000-0000-000000000002', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', '44444444-4444-4444-4444-444444444444', 4, 'The examples were useful and the documents helped reinforce the video.')
ON CONFLICT (id) DO UPDATE
SET
  rating = EXCLUDED.rating,
  comment = EXCLUDED.comment,
  updated_at = NOW();

COMMIT;
