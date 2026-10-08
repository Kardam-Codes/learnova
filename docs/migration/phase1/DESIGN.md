<!--
File: DESIGN.md
Owner: BOTH CAN ADD
Purpose: Specify the storage model and compatibility rules for the MongoDB migration.
What it is: Phase 1 design deliverable; no live database initialization or cutover.
Prepared: 2026-10-07 (Asia/Calcutta)
-->

# Phase 1 - MongoDB storage and API design

**Design status:** Complete for implementation. Server acceptance of validators/indexes and transaction behavior will be verified in Phase 2. Phase 0 restore and isolated write-flow verification remain open and are not represented as passing.

**Confirmed user requirements:** Preserve every existing Learnova record and existing access. Reconfigure the existing MongoDB service for the development replica set when infrastructure work begins. Do not replace or discard existing MongoDB databases as part of that reconfiguration.

**Scope of this phase:** Specification files and an offline exporter. No application persistence has switched, no service configuration has changed, no packages have been installed, and no database records have been altered.

## 1. Deliverables and how they fit together

| File | Purpose |
| --- | --- |
| `mongodb-schema-v1.json` | MongoDB collection validators, named index definitions, source-field mappings, and operational collection shapes |
| `postgres-openapi-baseline.json` | Existing FastAPI OpenAPI contract, exported before runtime migration |
| `endpoint-inventory.json` | All 40 current API operations, parameter/request definitions, and documented response statuses |
| `DESIGN.md` | Implementation decisions, query patterns, behavior invariants, and phase gate |
| `../../../backend/db/migration/export_phase1_spec.py` | Reproducible exporter using the private Phase 0 schema inventory |

The exporter reads a saved schema inventory and the application's OpenAPI definitions. It does not connect to MongoDB, create collections, or write PostgreSQL records. Live response fixtures stay in the ignored `.local/migration-baseline/` directory because they contain application data.

Reproduce the design artifacts from the recorded snapshot:

```powershell
python backend/db/migration/export_phase1_spec.py --baseline-manifest '.local/migration-baseline/20261007T122950131750Z/manifest.json'
```

The relative exporter path in the table is a repository path description; use the command from the project root.

## 2. Decisions and their basis

| ID | Decision | Basis/status |
| --- | --- | --- |
| P1-01 | Preserve all existing records, IDs, hashes, histories, and current access | Confirmed by user |
| P1-02 | Reconfigure the existing MongoDB service; retain its data directory/databases | Confirmed by user; actual reconfiguration belongs to Phase 2 |
| P1-03 | Use synchronous PyMongo with existing synchronous routes/services | Existing execution model; avoids unrelated async conversion |
| P1-04 | Use UUID strings as domain `_id` and reference values | Existing API/JWT identities; migration should not change identity |
| P1-05 | Preserve API names, endpoint paths, option ordering, and ID meanings | Existing frontend depends on them |
| P1-06 | Store money in integer paise; preserve API price units | Exact conversion of current SQL numeric values and current payment amounts |
| P1-07 | Use 13 domain collections and 3 operational collections | Full preservation includes global tag metadata and association IDs |
| P1-08 | Preserve empty quizzes and current publication flags; require a valid definition before scoring | Three empty quizzes belong to three published courses; no automatic deletion/unpublishing |
| P1-09 | Import stored progress/balances without silently repairing historical discrepancies | Preserve source data and report differences separately |
| P1-10 | Existing paid enrollment remains valid even when a provider order is absent | Preserves confirmed existing access; no fabricated payment record |
| P1-11 | Retain first-user bootstrap behavior using an atomic fixed state record | Matches current behavior while addressing the count-then-insert race |
| P1-12 | Retain per-course content slugs; support explicit course context for ambiguous admin lookups | SQL currently permits duplicate slugs across courses |
| P1-13 | Preserve legacy time reporting initially | `last_position` aggregation is not reliable elapsed-time measurement; redesign is a separate feature |
| P1-14 | Add an optional quiz submission idempotency header with explicit frontend support | Current request body can stay compatible; transaction alone cannot deduplicate HTTP retries |
| P1-15 | Keep legacy deletion/nulling and point-balance retention semantics | Existing SQL constraints and service behavior |
| P1-16 | Avoid new arbitrary product limits during storage migration | Existing API has no question/option/attachment count cap; BSON size remains the hard bound |

The decisions above are engineering specifications within the authorized migration. The repository location/initialization and permission to create an isolated PostgreSQL restore database remain unanswered earlier questions. They do not prevent writing this design, but they remain release-readiness prerequisites.

## 3. Domain collections and preservation mapping

All 19 source tables and every source column are represented in the machine-readable `source_mapping`. Parent foreign keys omitted inside an embedded object are reconstructible from the containing parent ID. No source field is discarded merely because it is not displayed in React.

| Collection | Source | Aggregate/reference design |
| --- | --- | --- |
| `users` | `users` | One user; same ID, password hash/provider identity, role, active flag, and timestamps |
| `courses` | `courses` + embedded `course_tag_map` | Course metadata plus tag membership objects; user responsibility references |
| `tags` | `course_tags` | Global catalog; preserves tag ID/name/date and unused tags |
| `course_content` | `course_content` + embedded `content_attachments` | One independently editable lesson/content item with attachment metadata |
| `quizzes` | `quizzes` + embedded questions/options/reward rules | One quiz definition linked to its course and content item |
| `enrollments` | `course_attendees` | Unique course/user relationship with source, payment status, and enrollment date |
| `quiz_attempts` | `quiz_attempts` + embedded `quiz_attempt_answers` | One submission, score/reward, and original selected-answer records |
| `course_progress` | `course_progress` | Unique course/user summary; stored fields preserved at import |
| `content_progress` | `content_progress` | Unique content/user state plus course reference |
| `learner_points` | `learner_points` | User balance and badge; imported without speculative reconstruction |
| `point_events` | `point_events` | Separate event ledger; signed deltas and historical nullable references |
| `reviews` | `course_reviews` | Unique course/user review and original timestamps |
| `payment_orders` | `course_payment_orders` | Provider order state, exact amount/currency, IDs, and dates |

### 3.1 Why tags differ from the initial roadmap

The initial roadmap suggested storing only tag names inside each course. Full preservation requires the global `course_tags` IDs and creation dates, unused catalog entries, and `course_tag_map` IDs too. Therefore:

- `tags._id` is the old tag ID.
- `tags.normalized_name` is a trimmed/lowercase lookup key; `tags.name` keeps the original display spelling.
- `courses.tags[]` contains the old association `id`, `tag_id`, and a cached display `name`.
- Source association `course_id` is the containing course `_id`.
- Course API responses continue to return an array of tag-name strings.
- Existing course edits can reuse the same catalog record; there is no new tag-management UI.
- A future tag rename must update cached names or resolve names from `tags`; no rename feature is introduced now.

### 3.2 Quiz and answer structure

Questions contain their original IDs, text, timestamps, ordering, and embedded options. Options contain their original IDs, text, correctness, and ordering. Reward rule objects keep their original row IDs, attempt threshold, and points.

Attempt `answers[]` preserves one embedded record per original selected-option row: `id`, `question_id`, `selected_option_id`, and `is_correct`. Multiple selected options for one question remain multiple records. The old `attempt_id` is reconstructed from the containing attempt `_id`. This deliberately preserves original answer-row identity rather than collapsing rows into a lossy single-choice field.

New attempts may additionally contain `quiz_version`, course/content references, `submission_key`, and a submission fingerprint. Legacy quiz versions are unknown and can be null. Existing records must not be given invented historical version claims.

### 3.3 Operational collections

| Collection | Purpose | Initialization |
| --- | --- | --- |
| `app_metadata` | Atomic first-administrator bootstrap state | Fixed `_id: auth_bootstrap`; imported accounts mean bootstrap is already claimed |
| `schema_migrations` | Applied schema version and specification checksum | Written only after initialization is verified |
| `quiz_attempt_counters` | Unique quiz/user attempt allocation | Set from imported maximum attempt numbers; new counters start at zero |

These are implementation records, not extra frontend entities. Migration-run reports can stay in private local files initially; a persistent `migration_runs` collection is unnecessary for the current project size.

## 4. Types, defaults, and conversion rules

### 4.1 Identifiers and naming

- Domain primary keys use canonical lowercase UUID strings; newly created domain records also use UUIDs.
- Embedded source records keep `id`; top-level primary keys become `_id`.
- Foreign references remain UUID strings. Operational fixed keys use their documented special shape.
- MongoDB uses snake case internally. Serializers expose existing camel-case API fields.
- Learner course/content IDs that currently contain slugs continue to contain slugs. Admin content `id` continues to be a UUID alongside its `slug`.
- `nextContentId` is the next content slug, not a MongoDB `_id`.

### 4.2 Money

`courses.price` converts from SQL numeric rupees to `courses.price_paise` using decimal arithmetic. Require an exact two-decimal conversion; do not round unexplained extra precision silently. Course currency is explicitly INR because that is the current configured course/payment model. A different currency needs a deliberate extension and cannot be inferred from a record with no currency field.

Payment `amount_paise` is already an integer and is copied unchanged. API course `price` remains in current units, while checkout `amount` remains paise. Maximum representable amounts must remain within valid provider/service ranges; a storage type change is not permission to charge larger amounts.

### 4.3 Dates, numbers, and nulls

- Use BSON dates with timezone-aware UTC decoding; serialize dates at the existing API boundary.
- PostgreSQL microseconds may lose sub-millisecond precision in BSON; reconciliation compares using that documented normalization.
- Scores/completion percentages use doubles with current two-decimal rounding and range checks. They are not currency.
- Optional `google_id` and `provider_payment_id` are omitted when absent. Their partial unique indexes cover actual strings only.
- Other source nullable fields may remain null. Required source fields remain required.
- `schema_version: 1` is required on domain documents and appropriate operational records.
- Preserve source timestamps during import; set application timestamps explicitly on new writes.
- Normalize email as trimmed lowercase consistently across creation, login, availability, and Google flows. The source audit found no collision groups; the final import still repeats the check.

### 4.4 Bounds and existing values

The stored source data currently has at most three questions per quiz, three options per question, and two attachments per content. Those observed maxima are not product limits.

Retain the existing Pydantic text/password/rating limits at the API. Database validators preserve SQL type/range requirements and allow empty quiz arrays so historical definitions import successfully. Before a write, calculate the assembled BSON size and reject a document that exceeds MongoDB's permitted size. Do not invent new question/attachment count limits during migration. Product-specific limits can be added later with an explicit compatibility decision.

## 5. Validation specification

`mongodb-schema-v1.json` contains collection validators with strict validation, error action, required fields, BSON types, enum values, numeric ranges, and documented properties. Unknown storage properties are rejected; schema upgrades add fields through a versioned initializer rather than relying on incidental writes.

Cross-field rules included in the specification:

- Local users have a password hash; Google users have a Google ID.
- Payment-access courses have a positive price.
- Quiz content has quiz mode; lesson content has video/document/image mode.
- Positions/point balances/counts are nonnegative; display/attempt order and payment amounts are positive.
- Ratings are 1-5, scores and completion percentages 0-100.
- Stored role/provider/status/mode strings match the source enums.

Service checks still enforce:

- Existence and ownership of referenced users/courses/content/quizzes.
- No repeated question IDs, option IDs, question ordering, option ordering, or tag membership inside one document.
- A quiz has questions/options and valid correct-answer sets before it can be scored.
- Submitted question coverage and zero-based option indexes are valid.
- Published/unpublished access, enrollment rules, and sequential lesson locks.
- Cross-document consistency and external payment authorization.

The JSON is an initialization input specification, not a claim that the live MongoDB server has accepted it. Phase 2 must exercise valid/invalid documents, partial indexes, and rollback on the actual configured server before these definitions are marked verified.

## 6. Index specification and query patterns

The machine-readable index list includes explicit names, ordered field pairs, uniqueness, and partial filters. Initialization must compare names and specifications, report incompatible existing definitions, and avoid silent index drops.

| Screen/operation | Query pattern | Main index/strategy |
| --- | --- | --- |
| Signup/login/email availability | Normalized email equality | Unique `users.email` |
| Google login | Google ID or normalized email | Partial unique Google ID plus email |
| Admin user selector | Role filter | `users.role` |
| Catalog | Publication/visibility plus user enrollment/progress | Course filter index; batch related lookups |
| Course detail | Course slug, ordered content, enrollment/progress | Unique course slug and course/content ordering |
| Course tags | Global normalized name and embedded course links | Unique tag lookup; serialized display-name array |
| Content route | Course ID and content slug | Unique compound course/slug |
| Next lesson | Course ID and greater display order | Compound course/order index |
| Attendees | Course ID; joined users | Unique course/user enrollment index, batched user IDs |
| Learner enrollments | User ID and courses | Reverse user/course enrollment index |
| Progress update | Content/user; aggregate course/user | Unique progress indexes and transaction |
| Quiz definition | Content ID | Unique quiz/content index |
| Quiz submission | Quiz/user/counter; submission key | Unique attempt/counter/retry indexes |
| Profile points | User ID | Unique balance/user |
| Point history | User/date | User/creation date plus partial attempt uniqueness |
| Reviews | Course/user upsert; course/date list | Unique course/user and course/date indexes |
| Payment verification | Provider order/payment identity | Unique provider IDs; partial optional payment ID |
| Reporting | Enrollments joined to course/user/progress | Indexed references and aggregation without fan-out multiplication |

Do not introduce one query per course or lesson when a batched lookup can serve a screen. Index additions after this design require a measured query need. Performance improvements are verified by timing/query plans, not inferred from the database name.

## 7. HTTP compatibility contract

The OpenAPI snapshot has 40 operations and 27 generated schemas. It freezes documented paths, methods, parameters, payloads, response models, and default documented statuses. Many current service responses do not have explicit response models; the 76 Phase 0 response fixtures supplement OpenAPI for those cases.

OpenAPI does not list every runtime 401/403/404/409 response because the app uses custom dependencies/service checks. The absence of a status in `documented_responses` is not permission to remove that runtime behavior.

Compatibility requirements:

- Existing registration returns its current successful HTTP status, not an assumed REST convention.
- Keep `access_token`, `token_type`, and user response fields. Do not leak MongoDB storage fields, hashes, or provider internals.
- Keep request casing for course creation, content modes, payment verification, and quiz answers.
- Keep `selectedOptionIndexes` as an array; multiple-selection support remains.
- Preserve `GET /auth/check-email` and its `isAvailable` response.
- Keep validation failures as readable 422 responses supported by the current frontend error parser.
- Map duplicate identities/conflicts intentionally; do not leak raw driver errors.
- Add useful sanitized 503 database-unavailable responses; handle CORS so the browser receives the error body.
- Retain existing optional upload form fields and static URL behavior.
- Preserve current report fields, date/percentage formatting, and summary/filter semantics.

### 7.1 Compatible additions

**Admin content context:** Keep `/admin/content/{content_slug}`. Add optional `courseSlug` context for reads/updates/deletes. A globally unique existing slug works without the new parameter. An ambiguous context-free slug returns a conflict requesting context; it never mutates the first matching course. Update the API client to supply context when the editor already knows the course. Do not rename existing slugs or impose new global uniqueness.

**Quiz retry identity:** Add optional `Idempotency-Key` header, bounded to 128 characters. For the updated frontend, generate one key per submission and reuse it on retry; a deliberate new attempt receives a new key. Unmodified clients can submit without it but do not gain cross-request deduplication guarantees. A key is scoped to quiz/user, and reuse with a different canonical answer payload is rejected as a conflict.

These additions are documented changes to implement in the relevant later phases, not claims that the current exported OpenAPI already contains them.

## 8. Transactions and concurrency behavior

### 8.1 Bootstrap

Initialize the fixed bootstrap document before accepting registrations. Importing any existing users closes bootstrap. Preserve the existing super administrator rather than promoting another signup.

For a genuinely empty seed/test database, the first-user claim and user insertion occur in one session transaction. Concurrent registrations compete on the same state document; transient conflicts are retried and the losing request gets its ordinary selected role after bootstrap is claimed. Email uniqueness still applies independently. Never reopen bootstrap automatically after users are deleted.

### 8.2 Progress

Content and course-progress updates share a transaction. Recompute summary counts from the relevant content records and write the shared summary so concurrent updates to different lessons cannot commit a stale aggregate. Apply retry handling and test an interleaved completion case.

Preserve current stored summaries during import. A normal subsequent learner update can recalculate according to the agreed algorithm; a bulk historical correction is a separately recorded operation. Preserve baseline empty-course/time semantics until an intentional behavior correction is tested and documented.

### 8.3 Quiz submission

One transaction allocates the attempt, inserts answers/result, updates progress, adds points/badge, and inserts one reward event. All helpers receive the same session.

1. Resolve course/content/quiz and enforce enrollment/locks.
2. Validate questions, option indexes, and scoring against the loaded quiz version.
3. Look up a provided submission key; return the existing matching submission or reject a mismatched payload.
4. Atomically allocate the next counter value while enforcing the attempt limit.
5. Insert the attempt and selected-answer records.
6. Update content/course progress and resulting balance/badge.
7. Insert an event linked uniquely to the attempt.
8. Commit and return the current API result.

Retry callbacks must not make external network calls. Unique-index races for an already committed retry should resolve to the recorded submission result, not award again. Counts alone are insufficient to allocate attempts.

Preserve fourth-plus reward fallback and exact-set scoring for multiple selected answers. Preserve question/option IDs on unchanged definitions. Increment quiz version on meaningful definition/reward changes; imported historical versions remain unknown when no source evidence exists.

### 8.4 Payments

Keep Razorpay signature verification and request helpers. External order creation is outside retryable database transactions. Persist order/pending enrollment consistently and define reconciliation for a provider order created when local persistence fails.

Verification binds stored order, course, and authenticated user. Paid order and paid enrollment transition together. Repeated verification of the same payment succeeds safely. A conflicting payment ID fails. Paid enrollment must not be downgraded by checkout retries.

Legacy paid enrollment without a stored order is retained. Do not manufacture a provider payment, reverse access, or require the user to pay again solely because the migration cannot find a historical order.

## 9. Deletion and reporting

### 9.1 Deletion

Match the original SQL cascade/nulling behavior first: course/content/quiz dependencies are deleted; references in retained point events are cleared where SQL used `SET NULL`; existing point balances are not automatically reduced. Attachment metadata is embedded and disappears with content, but deleting disk assets requires separate reference-aware logic and is not added here.

Retain the global tag catalog when a course is deleted. Deleting a course removes its embedded tag memberships, not tags shared by other courses or unused global catalog records.

After content mutation, summary recalculation must be explicitly tested; a source cascade alone is not evidence that derived progress was updated. Large-data asynchronous deletion is deferred unless the measured project workload requires it.

### 9.2 Reporting

Start from enrollments, retain learners without progress, and join course/user/progress records through batched queries or aggregation. Aggregate one-to-many child rows before combining them so counts/time are not multiplied accidentally.

Preserve report date formatting, percentage formatting, row ordering, status fallback, and whether summary cards cover all records or the filtered result. Keep legacy `timeSpent` output initially and document that it derives from `last_position`; do not label it as newly accurate elapsed learning time.

## 10. Schema lifecycle and Phase 2 handoff

Phase 2 will consume the specification and:

1. Establish the project environment and verified driver version.
2. Back up existing MongoDB databases/configuration before changing the existing service.
3. Configure the local development replica set without replacing its data directory or deleting databases.
4. Confirm replica-set readiness and transaction commit/rollback. A single-device development replica set is not a high-availability deployment.
5. Initialize only a dedicated Learnova development/test database; do not apply validators to unrelated databases.
6. Apply named indexes and validators with schema-version/checksum tracking.
7. Insert representative valid/invalid fixtures, verify optional unique fields, and test session propagation/rollback.
8. Add lifecycle/readiness handling without switching partially migrated domain flows into real use.

Schema changes must be explicit. If the spec changes before activation, regenerate artifacts and record the checksum. Once applied to a populated database, use a new migration/version with a data conversion and recovery plan; do not silently overwrite the migration ledger or drop incompatible indexes.

## 11. Phase 1 verification and remaining gates

Design verification performed:

- All 19 source tables and all their columns are covered by a destination or reconstructible parent relationship.
- Thirteen domain collections and three operational collections have validator/index definitions.
- Named indexes refer to declared storage fields and have no duplicate names per collection.
- Required validator fields exist in their property declarations.
- Existing OpenAPI export covers all 40 operations and retains the current 27 schemas.
- Design artifacts parse as JSON and can be reproduced from the recorded source schema.

The checks above validate specification consistency, not live MongoDB behavior. No runtime test result is invented for a phase that has not run.

Phase 1 is complete as a design deliverable. Before any cutover or release, Phase 0 still requires a successful restore/recovery rehearsal and isolated write-flow baseline, and the intended Git repository must be settled. Before Phase 2 can be reported complete, server reconfiguration, version/dependency checks, validator/index execution, and real transaction tests must pass.

## 12. Sources

This design uses the official sources already researched in the main roadmap:

- [MongoDB embedding guidance](https://www.mongodb.com/docs/manual/data-modeling/embedding/)
- [MongoDB schema validation](https://www.mongodb.com/docs/manual/core/schema-validation/)
- [Unique indexes](https://www.mongodb.com/docs/manual/core/index-unique/) and [partial indexes](https://www.mongodb.com/docs/manual/core/index-partial/)
- [Transaction deployment requirements](https://www.mongodb.com/docs/manual/core/transactions-production-consideration/)
- [PyMongo transaction behavior](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/crud/transactions/)
- [PyMongo client lifecycle](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/connect/mongoclient/)
- [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/)

Collection boundaries, preservation rules, and compatibility additions are Learnova design decisions derived from the inspected source and confirmed retention requirement.
