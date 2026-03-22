-- File: 005_quiz_attempt_answers_msq.sql
-- Owner: BOTH CAN ADD
-- Purpose: Allow quiz attempts to store multiple selected options per question.
-- What it is: A follow-up migration for learner MSQ submissions.

BEGIN;

ALTER TABLE quiz_attempt_answers
DROP CONSTRAINT IF EXISTS quiz_attempt_answers_attempt_id_question_id_key;

ALTER TABLE quiz_attempt_answers
ADD CONSTRAINT quiz_attempt_answers_attempt_id_question_id_selected_option_id_key
UNIQUE (attempt_id, question_id, selected_option_id);

COMMIT;
