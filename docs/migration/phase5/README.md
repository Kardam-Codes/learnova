# Phase 5: MongoDB learner reads and enrollment

MongoDB now supports learner catalog/profile, course detail, review reads, lesson/quiz
reads, and free enrollment. The working app retains its PostgreSQL selection; the
persistent migration target has not received real records. Tests and source rehearsals
use generated disposable databases on the existing local replica set.

## Storage selection and remaining phases

`COURSES_STORAGE=postgres|mongo` selects the learner service for every `/courses` route.
It defaults to `postgres` and is frozen per FastAPI lifespan. MongoDB learner storage
requires both `AUTH_STORAGE=mongo` and `ADMIN_STORAGE=mongo` so the converted identity,
authoring, and learner modules use the same configured database. Invalid combinations
fail startup. MongoDB schema/auth readiness and persisted-user authorization are reused.

`backend/modules/courses/storage.py` selects the implementation.
`backend/modules/courses/mongo_service.py` provides the converted operations. Existing
PostgreSQL behavior remains available for the working app and read-only comparison.
MongoDB failures return sanitized JSON 503, with CORS, and never fall back to PostgreSQL.

All learner routes use the selected service, including writes assigned to later phases.
In MongoDB mode, valid progress/review-write requests currently return 501 until Phase 6,
quiz submissions until Phase 7, and checkout/payment verification until Phase 8. These
explicit guards prevent MongoDB users from accidentally writing unrelated PostgreSQL
records. Invalid request bodies still fail Pydantic validation first. PostgreSQL mode
retains its original implementations of these routes.

Admin reporting remains PostgreSQL until Phase 9, and `/db/health` still checks both
configured databases. This phase does not claim a MongoDB-only complete application or
activate mixed storage for real users. The prior working-app activation/identity-bridge
decision remains pending. No local `.env` storage selection was changed.

## Catalog and profile

Catalog reads batch published courses, the current user's enrollments and summary
progress, content metadata, and content progress, then load the points profile. Query
count does not grow by one per course or content item. The integration command listener
verifies six catalog domain-service queries for both 2 and 12 courses and after growing a course from
4 to 24 content items. These counts exclude auth/readiness and connection handshakes.
This is a batching check, not a performance benchmark.

Existing fields and behavior are preserved:

- Course/public IDs remain slugs, while persisted UUIDs remain unchanged.
- Embedded tag display names, rupee prices, cover-image fallback, publication filtering,
  available/enrolled course grouping, and purchase/start flags retain their current shape.
- Both visibility values are accessible to authenticated users as before; learner routes
  still require authentication. Unpublished courses are omitted and their detail/content/
  enrollment routes return 404. Missing course lookups also return 404.
- A stored enrollment grants content access when its status is `paid` or `not_required`.
  `pending` remains locked. Historical paid access works without a provider payment order.
- Profile name comes from the persisted authenticated user. Points/badge values are read
  unchanged, with the existing zero/Newbie default and badge-tier definitions when absent.
- Resume preference remains in-progress, then unstarted, then completed, in content order,
  with the stored current-content pointer taking precedence for the resume slug.
- The legacy resume-mode choice still comes from the preferred content item, which can
  differ from the stored resume slug's mode. This phase does not silently change that API
  behavior. A foreign-course resume pointer is ignored rather than exposing another course.

## Detail, content, quizzes, and review reads

Course detail batches enrollment, ordered content, content progress, quiz aggregates,
summary progress, reviews, and user names. The listener verifies eight queries at both
4 and 24 content items. Responsible-user and review-author names share one lookup.
Stored summary percentages/counts are returned without historical repair or writes.
Existing empty-course and zero-count fallback behavior is retained.

Content lookup always uses the requested course. Duplicate content slugs across courses
remain valid and resolve independently. Attachments retain ordered IDs, labels, and URLs;
the learner attachment contract still omits admin-only attachment type. `nextContentId`
continues to be the next content slug, and is null at the end.

The user confirmed on 2026-10-08 that **enrolled learners may open lessons in any order**.
Quizzes require completion of all preceding non-quiz lessons. Another user's progress
cannot unlock them. An initial quiz with no preceding lessons is available to enrolled
users. Unenrolled/pending users receive 403 on direct content/quiz requests. Overview
metadata, URLs, and learner quiz questions retain the existing preview contract and lock
flags; no new preview-redaction policy is inferred.

Learner quiz serialization is separate from admin builder serialization. Questions expose
their original UUID, prompt, ordered answer text, and `allowsMultipleAnswers`; correctness
flags, correct indexes, option IDs, hashes, and internal database properties are excluded.
Rules/reward fields retain their existing format. Empty definitions and questions without
options keep the SQL inner-join read behavior; draft definitions are not deleted or
unpublished. Scoring/attempt validation remains Phase 7.

Review reads are included here because the course-detail response already includes them.
MongoDB detail no longer needs SQL to populate its review tab. Average/count, author names,
rating/comment, own draft, and enrollment flag retain their contract. The separate reviews
GET keeps the legacy behavior for missing/unpublished courses: empty or existing review
data with `isEnrolled=false`, rather than introducing a new 404. Review writes remain Phase 6.

Reviews sort by creation date and then UUID. The source contains one group with identical
review timestamps; the old SQL query has no tie-breaker. The final deterministic order
matches all saved source responses. The verifier can normalize only groups proven to have
identical full source timestamps; tests confirm it rejects reordering distinct timestamps
or changing review fields. No such review-order normalization is required for the final
source rehearsal. See [MongoDB sort consistency](https://www.mongodb.com/docs/manual/reference/method/cursor.sort/)
and [PostgreSQL ordering](https://www.postgresql.org/docs/current/queries-order.html).

## Enrollment transactions and shared deletion boundary

Enrollment resolves a published course and existing user within a session transaction,
then uses the same parent-course write boundary as admin mutation/deletion. The shared
helpers live in `backend/db/mongo/transactions.py`; the Phase 4 admin service now delegates
to them without changing its transaction semantics. Later dependent writes must reuse
this boundary to avoid read-existence/write-child races.

Free open-course enrollment upserts the unique course/user pair with `self/not_required`.
Existing enrollment UUID and enrollment date are retained. Already-authorized paid or
invited memberships return the detail without downgrading payment status or changing
membership source. Pending open memberships become free self enrollments as before.
Unpaid payment courses return 400; uninvited invitation courses return 403. Enrollment
does not create progress, points, attempts, or provider payment records.

The transaction uses snapshot reads, majority commits, a finite overall operation deadline,
driver transient retries, and bounded duplicate-key fresh-snapshot retries. The new
enrollment UUID/timestamp are generated once outside retry callbacks. Detail serialization
uses the same session before commit; a failure after the enrollment write rolls back that
write and the parent update. Concurrent self enrollments create one membership, concurrent
paid admin invitations retain paid access, and concurrent course deletion leaves no orphan.

Admin attendee/invitation operations remain the Phase 4 MongoDB implementation. Tests show
that a newly invited MongoDB-only identity can use learner reads/enrollment and appears
in that same attendee list, without requiring a PostgreSQL user row.

## Verification

From the project root, with the existing local replica set and development dependencies:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q --junitxml=.local\migration-baseline\phase5-all-tests.xml
.\.venv\Scripts\python.exe -m backend.db.migration.verify_phase5_baseline
```

The source rehearsal imports all 85 rows from all 19 SQL tables only into a guarded
temporary MongoDB database, compares the 142-column root/embedded mapping before and after
reads, and removes the temporary database. PostgreSQL fingerprints/schema remain unchanged.
It compares 76 saved responses in both modes, 17 additional admin details, and 180 learner
reads across all six source identities, including content/quiz access and missing courses.
Only the known UTC/BSON millisecond normalization of eight attendee responses is needed.
All other final source responses, including review order, match exactly. All 40 original
OpenAPI operations and 27 schemas remain preserved; Phase 5 adds no HTTP parameter/model.

Verification calls the real FastAPI routes and MongoDB directly. No frontend generated/mock
data code runs, so fallback data cannot satisfy a check. The frontend source is unchanged;
this phase does not claim browser-based end-to-end coverage of later-phase actions.

The suite covers the access/payment/publication matrix, all lesson modes, confirmed locks,
empty courses/quizzes, next/resume routing, safe quiz fields, points and historical summaries,
review reads/ties, new invitees, guarded future writes, database/CORS failures, configuration
freeze, batched query counts, concurrency, transaction rollback, and an injected real
transient retry after insertion. Prior auth/admin/infrastructure tests also run.

The final run passes **159 tests**: 46 learner/reconciliation, 39 admin, 37 authentication,
and 37 infrastructure. Python syntax and dependency compatibility checks pass.

Private test XML, source response fixtures, aggregate verification, and the detailed report
are in ignored `.local/migration-baseline/`. The root roadmap remains ignored.

Next phase: **Phase 6 learning progress and review writes**. Working-app activation,
content-type conversion policy, and the earlier Git/PostgreSQL recovery gates remain open.
