# Phase 6: MongoDB learning progress and review writes

MongoDB now supports lesson progress updates and course review submissions through the
existing learner routes. The working app still selects PostgreSQL. All MongoDB write
verification uses generated disposable databases; no persistent real-data import or
application cutover occurred.

## Routes and storage selection

The existing `COURSES_STORAGE` selector now implements these writes in MongoDB mode:

- `POST /courses/{course_slug}/content/{content_slug}/progress`
- `POST /courses/{course_slug}/reviews`

Request models, response fields, authentication, and route paths remain compatible.
`COURSES_STORAGE=mongo` still requires `AUTH_STORAGE=mongo` and `ADMIN_STORAGE=mongo`.
Selection is frozen for each FastAPI lifespan, with no PostgreSQL fallback. Local
`.env` selections were not changed. Quiz submission remains guarded with 501 until
Phase 7; checkout and payment verification remain guarded until Phase 8. Reporting
remains PostgreSQL until Phase 9.

The implementations are in `backend/modules/courses/mongo_service.py`. The reusable
summary calculation is in `backend/modules/courses/mongo_progress.py`.

## Progress access and accepted updates

The write resolves a published course, persisted user, authorized enrollment, and
content belonging to that course inside the transaction. Missing/unpublished courses
or missing content return 404; unenrolled/pending learners return 403. Both `paid` and
`not_required` enrollments grant access, including historical paid access without a
provider order. UUIDs, enrollment records, and existing access are retained.

Video, document, and image lessons accept `not_started`, `in_progress`, and `completed`.
Positions are nonnegative integers; an explicit zero replaces an earlier position.
Invalid status, negative/fractional positions, and integers outside BSON's supported
range return 422 without committing a partial write. Request validation remains the
existing Pydantic contract.

The user-confirmed access policy remains in force: enrolled learners may update lessons
in any order. Only quizzes require all preceding non-quiz lessons to be completed.
An ordinary progress request cannot update a quiz in any status: a locked quiz returns
403, and an unlocked quiz returns 400 directing the learner to quiz submission.
Another user's progress cannot unlock or count toward the current user's work.

## One transaction for lesson and course progress

Every write uses the shared parent-course write boundary and transaction runner in
`backend/db/mongo/transactions.py`. The same boundary is used by admin content changes,
course deletion, invitations, and learner enrollment. It serializes competing changes
to one course so snapshot reads cannot commit a stale aggregate after another lesson
update or create a child record after course/content deletion.

Within that transaction, the service upserts the unique content/user progress row,
recalculates the course/user summary, and serializes the response before commit. An
existing progress row pointing at another course returns 409. Failures after the
lesson write or after the summary write roll back both and the parent update. MongoDB
validator failures return sanitized 422; database failures retain sanitized 503/CORS
handling. Retries reuse UUIDs and request timestamps generated outside the callback.

The denominator is the course's **current content**, including quizzes. Only this
learner's progress rows referencing that content count. Foreign, orphaned, and other
users' rows cannot inflate completion; they are not silently deleted. Completion is
rounded to two decimal places, and incomplete count is total minus completed count.
Status is completed when all items are complete, in progress when any item is complete
or in progress, and otherwise yet to start.

Simultaneous completions of different lessons produce a summary containing both.
Repeated requests for one lesson retain a single progress record and count it once.
Lesson progress creates no quiz attempt, reward event, or points balance.

## Timestamps, empty courses, and content edits

The inspected PostgreSQL behavior is preserved while two optional policy questions
remain unanswered:

- The summary's `started_at` is set on its first progress upsert and then retained,
  including an imported null. Existing content/summary UUIDs remain stable.
- Each `completed` update refreshes that lesson's `completed_at`. Each recalculation
  yielding a completed course refreshes the course's `completed_at`. Moving back to
  another state clears the relevant completion timestamp; recompleting assigns the
  new request time. This is uniqueness protection, not a claim that repeated writes
  leave every timestamp unchanged.
- An empty-course calculation returns completed with 0%, matching the SQL count
  comparison. The helper is tested directly: an empty course has no lesson for the
  public progress route to update.

The user was asked whether completion times should instead remain stable until
reopening, and whether empty courses should instead be yet to start. Neither proposed
change is treated as approved. These are explicit compatibility defaults, not inferred
answers, and can be revised when the user chooses.

Following roadmap decision D11, admin content additions/removals retain historical
summary counts and percentages until the learner next updates progress. Deletion
removes dependent lesson progress and nulls a deleted current-content pointer. The
next ordinary write recalculates against the current content. There is no bulk repair
of imported historical summaries or automatic rewriting of another learner's history.
The Phase 7 quiz writer must reuse the same calculation and parent boundary.

## Review updates

Reviews require the same published-course, persisted-user, and enrollment checks.
The unique course/user upsert preserves the review UUID and creation time, updates
rating/comment and update time, and returns the existing review payload within the
transaction. A response failure rolls back the review and parent update.

Ratings remain integers 1–5, comments remain 3–2000 characters, and comments are not
trimmed, preserving the existing request contract. Review count, average rounded to
one decimal place, author names, own draft, and enrollment flag match the existing
response. The deterministic creation-date/UUID order from Phase 5 remains unchanged.
Concurrent reviews by different users produce the correct final average; simultaneous
submissions by one user retain one review. Review and course deletion cannot leave an
orphan review.

## Verification and limits

From the project root, using the existing local replica set:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q --junitxml=.local\migration-baseline\phase6-all-tests.xml
.\.venv\Scripts\python.exe -m backend.db.migration.verify_phase6_baseline
```

The full backend suite passes **217 tests** in 238.36 seconds: 60 progress/review,
44 prior learner/reconciliation, 39 admin, 37 authentication, and 37 infrastructure.
The new progress/review suite also passes independently in 71.42 seconds. It covers access and
publication checks, all lesson modes/statuses, position zero, invalid requests, quiz
bypass rejection, scoping, timestamp lifecycle, empty courses, rounding, content edits,
concurrent writes/deletes, real schema rejection, rollback at multiple write stages,
and real driver retry behavior. Converted writes also pass with PostgreSQL connection
helpers forced to fail.

The source rehearsal imports all 85 rows from 19 PostgreSQL tables into a guarded
temporary database. Before writes, it verifies the 142-column mapping and unchanged
records, 76 saved API responses in both modes, 17 admin details, and 180 learner reads
across all six source identities. Only eight known attendee responses need UTC/BSON
millisecond normalization. All 40 original OpenAPI operations and 27 schemas remain
compatible.

The rehearsal then exercises five lesson progress updates, two review upserts, and
two follow-up learner reads using an imported identity. It verifies preserved IDs and
start/creation times, completion/reopening behavior, position zero, summary math, and
unchanged unrelated records, including access, balances, attempts, and payments. The
temporary database is removed. PostgreSQL fingerprints/schema and all three prior
MongoDB database fingerprints remain unchanged.

No PostgreSQL write baseline was exercised: the earlier isolated restore/write-test
database decision is still pending. Verification uses real FastAPI routes and MongoDB,
so frontend demo fallback data cannot satisfy it. No frontend source changed, and no
new browser end-to-end, provider-payment, or quiz-submission coverage is claimed here.
Full-suite evidence and the detailed report are in ignored `.local/migration-baseline/`;
the root roadmap also remains ignored. The frozen v1 schema/checksum is unchanged.

The final audit confirms zero domain records, unclaimed auth bootstrap, and the original
schema ledger in the persistent development target; no generated test database remains.
MongoDB remains 8.3.7 on `learnova-rs`, and all three local storage selectors remain
PostgreSQL. Syntax compilation and dependency checks pass. The suite emits only the
existing upstream Starlette/AnyIO deprecation warning.

Next: **Phase 7 quiz attempts, points, badges, and safe retries**. Working-app activation,
content-type conversion policy, and the earlier Git/PostgreSQL recovery gates remain open.
