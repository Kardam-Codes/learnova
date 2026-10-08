# Phase 4: MongoDB admin authoring

MongoDB persistence is implemented for admin course, content, quiz, attendee, and
responsible-user operations. The current app retains its PostgreSQL selection while
the staging/identity-bridge decision remains pending. This phase does not import real
records into the persistent target or activate mixed database operation for users.

## Storage selection and boundaries

`ADMIN_STORAGE` accepts `postgres` and `mongo`, defaults to `postgres`, and is frozen
for each FastAPI lifespan. MongoDB admin mode requires `AUTH_STORAGE=mongo`; an
inconsistent configuration fails at startup. The configured process-owned MongoDB
client, schema version/checksum, auth readiness, and persisted role checks are reused.
Database failures return sanitized JSON 503 without PostgreSQL fallback.

`backend/modules/admin/storage.py` selects the implementation for the existing admin
routes. `backend/modules/admin/mongo_service.py` implements MongoDB authoring.
The existing PostgreSQL implementation remains available for operation and comparison.

The admin reporting endpoint continues to use PostgreSQL until Phase 9. Learner
services still use PostgreSQL until their phases are implemented. Uploaded bytes remain
local files served through the existing static URL convention. These boundaries mean
that setting both selectors to MongoDB does not yet make the full app MongoDB-only.
Do not activate the working app before the pending staging decision and remaining
identity/reference requirements are resolved.

## Course and content behavior

- Course list/detail/create/update/publish/delete preserve existing response fields,
  UUID identities, slug conventions, access rules, and instructor/admin authorization.
- Tags use the preserved global catalog with normalized lookup names. Courses embed
  membership UUIDs and tag references; unchanged memberships retain their IDs.
  Deleting a course retains its global tags.
- API prices remain rupees; storage uses integer paise. New request amounts use Decimal
  conversion with the existing PostgreSQL `NUMERIC(10,2)` rounding/range behavior.
  Existing SQL prices are already two-decimal values and import exactly without
  additional rounding. Payment access requires a positive price.
- Creator/responsible-user references must exist. Lessons support video/document/image;
  quiz content must use quiz mode. Empty quiz drafts remain valid stored definitions.
- Attachments are ordered embedded metadata with stable UUIDs. The current lesson
  editor omits attachment IDs, so unchanged label/URL/type triples also retain identity.
  Repeated IDs and IDs owned by another content item are rejected.
- Existing API models and text limits remain unchanged. As the Phase 1 design specifies,
  no arbitrary question/option/attachment count cap is introduced. Oversized BSON and
  integers that cannot be encoded produce 422 with transaction rollback.
- Existing duration-label parsing is preserved for comparison; this phase does not
  redefine the legacy calculation or historical progress summaries.

### Course context for content routes

The existing GET/PUT/DELETE `/admin/content/{content_slug}` routes accept an optional
`courseSlug` query parameter. The lesson editor now supplies its known course context.
An unambiguous old URL continues to work. An ambiguous context-free slug returns 409
before any mutation; an explicit course context resolves only that course's content.
No source slug is renamed to impose global uniqueness.

The PostgreSQL lookup also honors this context and resolves a single UUID before
mutation, so the updated frontend remains safe while the working app still uses SQL.
Original OpenAPI operation IDs and request/response schemas remain unchanged; the three
optional query parameters are the additive contract change in this phase.

## Quiz aggregate and transactions

Quiz creation inserts content and the complete quiz aggregate in the same session and
transaction. Update/delete synchronize the linked content and quiz. The generic content
endpoint creates a coherent empty quiz definition when asked to create quiz content.
Draft/empty source quizzes and publication flags remain preserved.

Questions, options, and reward rules retain existing IDs where applicable. New temporary
UUIDs from the real quiz editor become server-generated IDs; IDs belonging to another
quiz, repeated IDs, and moving an option identity between questions are rejected.
Question order and multiple correct choices remain supported. Definition/reward/attempt
limit changes increment the stored quiz version. Metadata-only changes do not increment
that version. Historical attempt answers, awarded points, and attempt counters survive
definition edits. Legacy attempts retain an unknown version rather than an invented one.
Submission validation/scoring and retry identity belong to Phase 7.

All multi-document mutations use snapshot transactions, majority commits, and the same
session through helpers. External file writes and invitation password hashing stay
outside retry callbacks. Transaction retries and duplicate-key snapshot retries are
bounded by the configured operation deadline. Slug collisions use unique indexes and
suffix retries. Child mutations also update the parent course as a shared write-conflict
boundary, serializing content order allocation and deletion against concurrent authoring.
Later learner writes must reuse this boundary when checking course existence and writing
dependent records; an existence read alone does not prevent a deletion race.

The internal `reorder_course_content` helper first moves items beyond occupied positive
orders, then assigns the final sequence in one transaction. It rejects incomplete or
repeated ID lists. No new reorder route or frontend feature is introduced.

## Deletion and paid-access preservation

| Operation | Removed | Retained or cleared |
| --- | --- | --- |
| Delete quiz or quiz content | Linked content/attachments, quiz definition, attempts/embedded answers, counters, content progress | Awarded point balance and events retained; quiz reference cleared; deleted attempt reference omitted; current-content pointer cleared |
| Delete lesson | Content/attachments and its content progress | Course summary retained; current-content pointer cleared when applicable; uploaded files retained |
| Delete course | Its content/quizzes and their dependencies, enrollments, progress, reviews, payment orders | Users, global tags, uploaded files, awarded balances and point events retained; deleted course/quiz/attempt references cleared |

The course progress percentage/count fields retain historical values after content edits
or deletion, matching the current SQL behavior. This phase does not silently repair them.
Later normal learner progress updates will use the Phase 6 algorithm; historical repairs
remain a separate decision.

Attendee additions reuse normalized existing email identities without renaming accounts.
New invitees keep the current learner-role and invitation-password contract. Unique
enrollments prevent duplicates. Repeated invitations cannot downgrade existing `paid`
access to `pending` or `not_required`, satisfying the user's access-preservation requirement.
No provider payment record is fabricated for existing paid access.

**Pending policy:** the user was asked whether changing quiz content into a lesson should
be rejected or delete dependent quiz/attempt history. No answer was inferred. MongoDB
content-type conversions currently return 409 and preserve history. Normal editing within
the existing content type works. This guard is explicitly provisional, not an approved
destructive conversion policy or a new conversion UI.

## Verification and source rehearsal

From the project root, using the existing local replica set and development dependencies:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q --junitxml=.local\migration-baseline\phase4-all-tests.xml
.\.venv\Scripts\python.exe -m backend.db.migration.verify_phase4_baseline
npm.cmd run build
```

`rehearsal_data.py` reads all 19 SQL tables in a read-only repeatable-read transaction.
Its importer refuses all databases except a generated `learnova_test_<32 hex digits>`
name and requires empty domain collections. It assembles all 13 domain collections,
preserving original embedded IDs and source fields, then closes imported auth bootstrap.
The disposable database is removed on success or failure. This is rehearsal tooling,
not the Phase 10 production importer.

The rehearsal reconstructs and compares every source row/field represented by the
142-column mapping, preserving all 85 source rows. It checks all 76 saved API responses
in PostgreSQL and MongoDB authoring modes, plus 13 content and 4 quiz detail responses.
Only `enrolledAt` is normalized to UTC and BSON millisecond precision; eight saved
MongoDB responses require that documented normalization. All other fields, ordering,
statuses, and additional detail responses match. The additive MongoDB health object is
excluded as documented in Phase 2. All 40 original operations and 27 schemas are checked.

Integration tests exercise authoring, stable IDs, correct/invalid modes and references,
role authorization, paid-access retention, duplicate races, ordering, deletion matrix,
historical answer retention, upload preservation, and actual validator failure after
content insertion. Failure injection checks full deletion rollback across collections;
concurrent content creation/course deletion leaves no orphan child. MongoDB authoring
routes are also checked with PostgreSQL connection helpers forced to fail.

The final Phase 4 run passes **113 tests**: 37 infrastructure, 37 authentication, and
39 admin. The frontend production build, Python syntax, and dependency checks pass.

Private response fixtures and reports live under ignored `.local/migration-baseline/`.
The detailed local roadmap remains ignored. The persistent development target still has
zero domain records; original PostgreSQL and MongoDB records remain unchanged.

Next phase: **Phase 5 learner catalog, content reads, and enrollments**. Full cutover is
still Phase 11. The Git repository decision and PostgreSQL restore/write-test database
permission remain open from Phase 0.
