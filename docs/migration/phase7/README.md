# Phase 7: MongoDB quiz attempts, rewards, and retries

**Status: backend implementation and source rehearsal are available; final policy and
frontend retry integration are pending. Phase 7 is not yet complete.** The working app
still selects PostgreSQL. MongoDB writes and the new schema extension have been exercised
only in generated disposable databases.

## Decisions needed to finish

The user was asked two questions, and neither answer is inferred:

1. Should empty/incomplete quizzes reject submissions until ready, or retain SQL's
   acceptance behavior? The recommended correction rejects submission while retaining
   every draft definition and historical record.
2. Should the retry protocol use the roadmap's optional `Idempotency-Key` header plus
   a stable frontend key, require a key, or keep the old client? The recommendation is
   optional headers so existing clients remain compatible.

The backend service already accepts an internal optional `submission_key`; the HTTP
router and frontend have not yet exposed or sent it. There is no claim of protection
against separately received HTTP retries without a retained key. The existing request
body and HTTP contract remain unchanged at this stage.

Until the draft policy is settled, isolated backend submissions retain SQL's inner-join
question selection, including zero-question scoring/acceptance. Drafts are not deleted,
silently unpublished, or rewritten. This is the inspected compatibility behavior, not
approval of the proposed alternative. The persistent target still has v1 only and quiz
writes return a clear setup 503 until the explicit receipt migration is applied.

## Atomic scoring and side effects

`backend/modules/courses/mongo_service.py` implements the quiz transaction; supporting
calculations are in `mongo_quiz.py`. It resolves a published course, persisted user,
authorized enrollment, course-scoped quiz content, and quiz definition. Both paid and
not-required memberships work, including historical paid access without an order.
Absent/pending enrollment is denied. All preceding non-quiz lessons must be complete
for that user; ordinary lessons retain the confirmed any-order access policy.

Submitted questions must exactly cover the scoreable question identities. Unknown,
missing, extra, or duplicate questions and duplicate selections are rejected. Options
use zero-based positions in `display_order`, with explicit range checks. Multiple
selections are correct only when they exactly match the set of correct options.
Question correctness is stored on every selected-answer row, matching the existing
answer-record shape. Scores round to two decimal places.

Duplicate rejection intentionally tightens the old SQL normalizer, which collapsed
repeated indexes and overwrote repeated question entries. Existing request models and
valid submissions remain compatible; HTTP body validation still rejects negative
indexes and empty selections before the service runs.

One transaction, using the shared parent-course write boundary, performs:

1. Counter initialization/reconciliation and guarded next-attempt allocation.
2. Attempt insertion with embedded selected answers and scoring metadata.
3. Quiz content completion and Phase 6 course summary recalculation.
4. Balance increment and resulting badge calculation.
5. Original response snapshot attachment and uniquely linked reward event insertion.

All writes share a session. Every UUID and request timestamp is generated outside the
retry callback. A failed write, response construction, validator rejection, or injected
failure rolls back the counter, attempt, progress, balance, receipt, event, and parent.
The driver handles transient retries; the shared runner bounds duplicate-key fresh
snapshot retries and the learner error wrapper supplies the overall deadline.

## Attempt history and rewards

Counters use the historical **maximum attempt number**, not count-plus-one. A missing
counter is initialized from history; a lagging counter is advanced to that maximum.
An atomic `attempts_used < max_attempts` update allocates the next attempt. A counter
ahead of history is retained rather than reduced. Existing migration rehearsal import
already initializes operational counters from imported maxima. Legacy attempts and
their unknown/null version metadata are not rewritten.

The configured reward for an exact attempt number is used; if absent, the last numbered
reward rule is used, preserving SQL behavior and fourth-plus fallback. With no rules,
the reward is zero. A submitted wrong answer still earns its configured reward and
completes the quiz, as before; no new pass threshold is introduced.

Each new point event references its attempt, protected by the existing unique partial
index. Historical events without a reliable attempt reference retain their original
fields. Imported balances are incremented, not rebuilt from guessed event links.
The shared balance write also resolves concurrent quizzes in different courses, so
neither reward is lost.

Badges use the resulting total: Newbie through 20, Explorer 21–40, Achiever 41–60,
Specialist 61–80, Expert 81–100, and Master from 101. This applies on first balance
insertion too, correcting SQL's unconditional first-insert Newbie default in accordance
with the Phase 7 roadmap. Existing stored balances/badges remain untouched until a
normal new submission updates that learner's balance.

## Internal retry semantics and recorded history

Internal keys are scoped to quiz/user, contain 1–128 visible ASCII characters, and
are optional. Without a key, each accepted request is a distinct attempt. Canonical
fingerprints ignore answer-list and selection ordering while preserving question
identity and the selected set. An identical repeated key returns the original seven
response fields, without changing even parent timestamps. A changed payload returns
409; legacy keyed rows lacking a recorded result cannot have totals guessed for them.

Replay still requires current authentication, publication, enrollment, and an existing
quiz. Once those checks pass, it precedes current prerequisites, definition validation,
and attempt allocation: a committed result can be retrieved after an edit or a lesson
is reopened, or after the attempt limit is reached. A deliberate new attempt needs a
new key. Deleted attempts are not recoverable through their keys under existing deletion
rules; balances/events retain the agreed cascade/nulling behavior.

New attempts record the loaded quiz version, scoring-definition SHA-256, scoreable
question count, selected IDs/correctness, and original response. The shared parent
boundary ensures scoring and metadata come from one coherent version relative to admin
edits. Full historical prompt/option snapshots are deferred: a digest identifies a
definition but cannot reconstruct its text after replacement. No answer-review feature
or reconstruction of already-deleted SQL history is claimed.

## Explicit additive schema extension

The frozen v1 schema and checksum remain unchanged. The new reviewed manifest is
`docs/migration/phase7/mongodb-quiz-receipts-v2.json`, applied explicitly by
`backend/db/mongo/quiz_schema.py`. It adds only optional `quiz_fingerprint`,
`question_count`, and `result_snapshot` properties to the quiz-attempt validator, plus
a separate version-2 ledger record. Collections and named indexes remain 16 and 28.
Existing documents retain domain `schema_version: 1` and remain valid without those
optional properties. No domain record is backfilled or rewritten.

For a prepared, quiescent development/test target, after v1 initialization:

```powershell
.\.venv\Scripts\python.exe -m backend.db.mongo.quiz_schema
```

This command has **not** been applied to the persistent development target yet. It is
guarded to that target or generated test database names; it never operates on unrelated
device databases. Full validator/index/ledger preflight precedes DDL. Unknown drift
stops the command. If interrupted between `collMod` and the ledger write, it resumes
only its exact reviewed additive validator. Repeat application preserves all data and
ledger dates. The v1 initializer recognizes a correctly recorded extension on reruns,
while still refusing unknown/checksum drift or an unrecorded extension. Quiz writes
require the extension ledger, while the previous converted operations retain v1
compatibility. There is no automatic DDL during application requests.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q --junitxml=.local\migration-baseline\phase7-all-tests.xml
.\.venv\Scripts\python.exe -m backend.db.migration.verify_phase7_baseline
```

The full backend-stage regression suite passes **320 tests** in 328.93 seconds: 104
quiz/schema, 60 progress/review, 43 prior learner/reconciliation, 39 admin, 37 auth, and
37 infrastructure. This includes the added cross-course, canonical replay, history/edit,
and deletion cases. There are no failures, errors, or skips; only the existing upstream
Starlette/AnyIO deprecation warning. These results supersede the earlier narrower runs.

The read-only source rehearsal preserves all 85 source rows from 19 tables and their
142-column mapping before writes; 76 saved responses in both modes, 17 admin details,
and 180 learner responses across six identities still match. Only the eight known
attendee timestamp precision normalizations are needed. Original OpenAPI operations
and schemas remain unchanged at this stage.

After repeating Phase 6's five progress/two review updates, it completes prerequisites
for an imported identity, exercises two quiz submissions, an internal keyed replay,
409 for key reuse with different answers, and three follow-up learner reads. Reward
events link one-to-one to new attempts; source balances/access and untargeted records
are preserved. HTTP retry-header integration is explicitly pending, so this rehearsal
does not claim an end-to-end keyed frontend submission.

The real source has four quizzes (three empty), three questions, **zero historical
attempts**, and one historical point event. Gapped legacy attempt allocation is therefore
tested with explicit disposable fixtures, not claimed as an observed source-data case.
No legacy point-event attempt link or balance reconstruction is invented.

PostgreSQL tables/schema remain unchanged and the temporary import is removed. No SQL
write baseline is claimed while the earlier isolated restore/write-test decision is
pending. Verification calls the real backend and MongoDB; frontend fallback data cannot
satisfy these checks. No frontend source/build or browser coverage has changed yet.
Private evidence is under ignored `.local/migration-baseline/`; the root roadmap remains
ignored. Payments/reporting and working-app activation remain separate later work.

The final backend-stage audit confirms zero persistent domain records, unclaimed auth
bootstrap, and the original v1-only ledger; no generated test database remains. All
three local selectors remain PostgreSQL, and MongoDB remains 8.3.7 on `learnova-rs`.
Original device database fingerprints, Python syntax, and dependency checks pass.
The persistent v2 extension, readiness decision, and HTTP/frontend retry integration
remain pending; these verified backend results do not mark all of Phase 7 complete.
