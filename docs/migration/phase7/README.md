# Phase 7: MongoDB quiz attempts, rewards, and retries

**Status: COMPLETE — implementation, schema setup, and final verification passed on
2026-10-08.** The working app still selects PostgreSQL. MongoDB writes
are exercised in disposable databases; the empty development target has the explicit
receipt schema extension but has not received a permanent data import.

## Approved policies and HTTP/frontend retries

The user approved blocking empty/incomplete submissions and using an optional
`Idempotency-Key` header on 2026-10-08. The existing JSON body remains unchanged.
Keyless MongoDB requests remain compatible and count as separate attempts.

`GET /courses/quiz-submissions/capabilities` advertises support for the selected
runtime. The frontend checks it before a new submission. PostgreSQL retains the
legacy keyless flow; it does not support protected retries, and explicit keyed
requests are rejected with 409 rather than silently ignoring the key. There is no
storage fallback. MongoDB advertises support even when schema readiness fails;
in that case submissions return setup 503 and the client retains their pending key.

In MongoDB mode, the frontend saves a UUID key and the original answers to tab-scoped
sessionStorage before sending. Records are scoped by API server/user/course/quiz and
survive reloads. Pending submissions lock answer editing and offer Retry submission.
Network/server failures preserve the same key and payload; definitive answer-validation
or draft-readiness rejection releases the pending record for correction. Confirmed
results are retained, so a failed course refresh cannot consume another attempt.
Start Quiz explicitly clears a confirmed result and starts a deliberate new attempt.
An unresolved submission must be retried first. A synchronous in-flight guard also
prevents duplicate clicks. Browser storage must work before a protected submission
can be sent; manually clearing storage removes the client's retry identity.

New MongoDB submissions return 409 when there are no questions, a blank question prompt,
fewer than two options, a blank option label, or no correct option on any question.
Every question must be ready; incomplete questions are never silently omitted from scoring.
Rejected submissions leave drafts, attempt counters, progress, balances, and rewards unchanged.
Authorized keyed replays still return the committed receipt after a later edit makes a quiz
unready; they do not create a new attempt. Drafts are not deleted, unpublished, or rewritten.
This is a deliberate correction to legacy SQL submission behavior; the working PostgreSQL
application's database selection is unchanged. Unprepared targets return setup 503
until the explicit receipt migration is applied.

Readiness regression verification: 111 quiz/schema tests passed on 2026-10-08,
including seven new rejection/restoration cases and committed-result replay after an
edit creates an empty definition. Existing PostgreSQL data/schema remain unchanged.
This scoped run supplements the earlier 320-test backend-stage run.

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

## Retry semantics and recorded history

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

This command was applied to the empty development target on 2026-10-08 with zero domain
records rewritten. Its prior collection definitions and upgrade evidence are retained
privately. It is
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
.\.venv\Scripts\python.exe -m pytest backend\tests -q --junitxml=.local\migration-baseline\phase7-final-all-tests.xml
.\.venv\Scripts\python.exe -m backend.db.migration.verify_phase7_baseline
node --test src/utils/quizSubmission.test.js
npm run build
```

The final full regression suite passes **333 tests** in 393.79 seconds: 117 quiz/schema,
60 progress/review, 43 prior learner/reconciliation, 39 admin, 37 auth, and 37 infrastructure.
No failures, errors, or skips; only the existing upstream Starlette/AnyIO warning.
Five frontend tests and the production build (90 modules) also pass. The final private
state audit confirms zero generated test databases and zero persistent domain records,
unclaimed bootstrap, and both schema ledgers. These results supersede the backend-stage run.

Historical backend-stage regression passed **320 tests** in 328.93 seconds: 104
quiz/schema, 60 progress/review, 43 prior learner/reconciliation, 39 admin, 37 auth, and
37 infrastructure. This includes the added cross-course, canonical replay, history/edit,
and deletion cases. There are no failures, errors, or skips; only the existing upstream
Starlette/AnyIO deprecation warning. These results supersede the earlier narrower runs.

The read-only source rehearsal preserves all 85 source rows from 19 tables and their
142-column mapping before writes; 76 saved responses in both modes, 17 admin details,
and 180 learner responses across six identities still match. Only the eight known
attendee timestamp precision normalizations are needed. Original OpenAPI operations
and all 27 original schemas remain compatible, with one optional retry header,
three existing optional admin context parameters, and additive capability/health routes.

After repeating Phase 6's five progress/two review updates, it completes prerequisites
for an imported identity, exercises two keyed HTTP quiz submissions, a keyed HTTP replay,
409 for key reuse with different answers, and three follow-up learner reads. Reward
events link one-to-one to new attempts; source balances/access and untargeted records
are preserved. Five frontend Node tests exercise retained retry state, lost-response/
reload recovery, deliberate new attempts, scope isolation, storage failures, definitive
rejections, and actual API header construction. A production frontend build passes.
This is API and frontend-module verification; no browser UI automation is claimed.

The real source has four quizzes (three empty), three questions, **zero historical
attempts**, and one historical point event. Gapped legacy attempt allocation is therefore
tested with explicit disposable fixtures, not claimed as an observed source-data case.
No legacy point-event attempt link or balance reconstruction is invented.

PostgreSQL tables/schema remain unchanged and the temporary import is removed. No SQL
write baseline is claimed while the earlier isolated restore/write-test decision is
pending. Verification calls the real backend and MongoDB; frontend fallback data cannot
satisfy these checks.
Private evidence is under ignored `.local/migration-baseline/`; the root roadmap remains
ignored. Payments/reporting and working-app activation remain separate later work.

The development target retains zero domain records and unclaimed auth bootstrap, with
the frozen v1 and additive v2 receipt ledgers. All three local selectors remain
PostgreSQL; MongoDB remains 8.3.7 on `learnova-rs`. Original device database fingerprints
match their backup. Final full-suite and cleanup evidence is recorded in the private
Phase 7 report and `phase7-final-state.json`. Working-app cutover, payments,
reporting, PostgreSQL restore/write-baseline checks, and final full migration remain
separate work.
