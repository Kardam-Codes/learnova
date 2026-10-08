# Phases 9 and 10: verified on 2026-10-08

The initial code-only instruction was followed by authorization to complete
Phase 11 and run checks. Preserved-data import, repeat/resume, synthetic migrated
password login, PostgreSQL restore/write checks, MongoDB backup/restore, rollback
planning and volume measurements passed. Private evidence is under
`.local/migration-runs/phase11-20261008T115646179067Z`.

## Phase 9: reporting and workload tools

`backend/modules/admin/mongo_reporting.py` replaces the SQL view when
`ADMIN_STORAGE=mongo`. PostgreSQL remains the default. The existing report URL,
authorization, response fields and status filter remain intact.

The aggregation starts from enrollments, joins existing users and courses, and
looks up course progress and the sum of content positions independently. It
retains enrollments with no progress and avoids multiplying content positions.
Cards cover the entire report, regardless of the selected filter. SQL's NULL
status semantics are retained: a missing progress row displays `yet_to_start`,
but contributes only to Total Participants and does not match the explicit
`yet_to_start` filter. Changing that discrepancy is a separate product decision.
The reported time continues to be the sum of `last_position`, formatted as
hours:minutes; it is not a new elapsed-time measurement.

One snapshot transaction supplies all cards and rows. The response remains
unpaginated, matching the existing contract. Two batched English name sorts
preserve source ordering while the lookup pipeline keeps indexed UUID joins.
Original report ordering matches the PostgreSQL fixture. Additional locale
coverage remains outside the preserved English_India dataset. Ordering
between rows with identical names is unspecified in the original SQL.

`backend.db.migration.workload` provides a separate staging volume generator
and measurement command. The generator clones a frozen source graph with
deterministic UUIDs, unique natural keys, disabled users, unusable password
hashes, synthetic emails and gateway identifiers. Free text is still copied;
the fixture is private and is not an anonymized dataset. It never calls a
payment provider. Seeding is empty-target-only and defaults to dry-run. A failed
partial seed requires a new unique target; the migration importer, not the
volume generator, supplies resume support.

Measurement records catalog, detail, report and, where accessible, quiz timings,
plus the report execution plan. Optional `--include-writes` measures review
updates only on disabled synthetic volume users in a unique test database.
It changes that disposable fixture. Quiz access gates still apply. Other domain
write timings and index/pagination decisions remain part of deferred validation;
no speculative performance indexes have been added.

## Phase 10: explicit frozen export and staging import

`backend.db.migration.transfer` has `prepare`, `export`, `import`, and
`verify-login` commands. Connection strings and the selected login password are read
from explicitly named environment variables, never echoed or included in the
export manifest. Do not put secrets directly into command-line arguments.

Export reads all 19 mapped tables, foreign-key relationships and the SQL report
view inside one read-only repeatable-read transaction in UTC. Tagged JSON cells
preserve UUIDs, exact decimals and timezone-aware timestamps. A manifest records
table columns, counts and SHA-256 checksums. A failed export leaves an incomplete
directory without a final manifest; use a new directory for the next export.
Bundles include personal data and password hashes and must stay under ignored
`.local/`. File checksums detect accidental changes, not malicious tampering;
only use trusted bundles.

Import requires an explicitly named `learnova_test_<32 lowercase hex digits>`
database, prepared with schema versions 1, 2 and 3. It cannot import into the
working PostgreSQL database or the existing migration development database.
There is intentionally no production activation command in this phase.

Before writes, import checks mappings, checksums, counts, duplicate IDs, foreign
keys, exact supported paise, BSON sizes, reviewed schema/index definitions and
mapped unique keys. Each assembled document is checked against the reviewed
MongoDB validator through a read-only `$documents` aggregation. This mechanism
passed integration verification against the installed server and preserved dataset.

Parent collections precede dependent collections. Original UUIDs, empty quizzes,
quiz answers, memberships and paid access are retained. Derived attempt counters
use the highest historical attempt number; historical quiz versions stay null.
Timestamps retain the approved BSON millisecond normalization. Balances and point
events are preserved and reconciled separately; no balancing event is invented.

Import is insert-only: exact existing source documents can be reused on resume,
but changed or extra records cause refusal. It does not blindly replace/upsert
existing application data. Private checkpoints bind a run ID to the export
checksum and target collection UUIDs. Each majority transaction commits a batch,
then atomically replaces its checkpoint. A commit-before-checkpoint crash can
resume because exact matching documents are accepted. Missing acknowledged
documents abort. A workspace-local OS lock excludes concurrent transfer/seed
processes targeting the same database from this checkout.

`--apply --confirm-writes-paused` is required for writes. This is an operator
acknowledgment, not an automatic traffic pause: stop all application, schema and
other-machine migration writers yourself before running it. Leave the working
app on PostgreSQL. Imported authentication bootstrap is finalized only after
source-field and SQL-report reconciliation succeeds. A complete rerun performs
reconciliation again and refuses post-import domain changes.

All source fields, embedded rows, status counts, reviews, answers, balances,
events and SQL report filters are reconciled before completion. Selected local
password login verification is separate, uses the actual auth service, and
outputs only a boolean. Neither tokens nor credentials enter the report.

The mapper currently assembles the complete source graph in memory; batches
bound database commands, not total export/import RAM. Large-dataset capacity
must be measured. Production activation, automatic reverse migration, webhook
payment redesign and UI behavior changes are outside these phases.

## Recovery and rollback tools

`backend.db.migration.recovery` provides `backup`, `restore`, and
`rollback-plan`. Backup is a consistent logical BSON snapshot of the single
selected application database, including operational records, validators and
indexes. Pause both data and schema writers. It does not back up MongoDB users,
server configuration, other databases, or external uploaded files.

Restore validates file checksums and frozen schema definitions, refuses any
nonempty target, and only writes to a different unique Learnova test database.
It reconstructs collections/indexes, restores BSON, and compares every collection
fingerprint. A failed restore retains its isolated partial target for inspection;
retry into another empty unique target. It never drops a database automatically.

Rollback planning requires paused writers and exact fingerprints matching a
reference backup made **after successful import and before cutover writes**.
It emits a private plan for all three PostgreSQL selectors; it never edits `.env`
or restarts the application. Any MongoDB change after that reference blocks the
plan. This conservative check includes operational metadata changes. PostgreSQL
source preservation and application revision still need independent verification.
After MongoDB accepts new writes, lossless rollback needs export/reconciliation;
merely changing selectors is insufficient. The original PostgreSQL restore gate
remains open until rehearsed, as recorded in the roadmap.

## Commands for the deferred verification session

These examples describe the commands; private artifacts record equivalent
executed rehearsals. Set the
named environment variables privately. Replace `<hex32>` and paths with unique
values; never reuse a working application database. Prepare target schemas with
the existing explicit v1/v2/v3 setup commands first, without seeding demo data.

```powershell
python -m backend.db.migration.transfer prepare --target-uri-env LEARNOVA_TARGET_URI --database learnova_test_<hex32> --apply --confirm-writes-paused
python -m backend.db.migration.transfer export --source-env LEARNOVA_SOURCE_DSN --output .local/migration-runs/export-01
python -m backend.db.migration.transfer import --target-uri-env LEARNOVA_TARGET_URI --database learnova_test_<hex32> --snapshot .local/migration-runs/export-01 --run-id import-01
# Only after stopping target writers and reviewing dry-run output:
python -m backend.db.migration.transfer import --target-uri-env LEARNOVA_TARGET_URI --database learnova_test_<hex32> --snapshot .local/migration-runs/export-01 --run-id import-01 --apply --confirm-writes-paused
python -m backend.db.migration.transfer verify-login --target-uri-env LEARNOVA_TARGET_URI --database learnova_test_<hex32> --user-id <selected-id> --password-env LEARNOVA_VERIFY_PASSWORD

# Use a DIFFERENT initialized empty test database for volume seeding:
python -m backend.db.migration.workload --target-uri-env LEARNOVA_TARGET_URI --database learnova_test_<other-hex32> --output .local/migration-runs/seed-plan.json seed --snapshot .local/migration-runs/export-01 --copies 10
python -m backend.db.migration.workload --target-uri-env LEARNOVA_TARGET_URI --database learnova_test_<other-hex32> --output .local/migration-runs/seed-result.json seed --snapshot .local/migration-runs/export-01 --copies 10 --apply --confirm-writes-paused
python -m backend.db.migration.workload --target-uri-env LEARNOVA_TARGET_URI --database learnova_test_<other-hex32> --output .local/migration-runs/measurement.json measure --repetitions 10

python -m backend.db.migration.recovery backup --target-uri-env LEARNOVA_TARGET_URI --database learnova_test_<hex32> --bundle .local/migration-runs/recovery-01
python -m backend.db.migration.recovery backup --target-uri-env LEARNOVA_TARGET_URI --database learnova_test_<hex32> --bundle .local/migration-runs/recovery-01 --apply --confirm-writes-paused
# Restore destination must be absent, not already schema-initialized:
python -m backend.db.migration.recovery restore --target-uri-env LEARNOVA_TARGET_URI --database learnova_test_<restore-hex32> --bundle .local/migration-runs/recovery-01 --apply --confirm-writes-paused
python -m backend.db.migration.recovery rollback-plan --target-uri-env LEARNOVA_TARGET_URI --database learnova_test_<hex32> --bundle .local/migration-runs/recovery-01 --output .local/migration-runs/rollback-plan.json --confirm-writes-paused
```

## Verification runbook

- Run the added reporting, transfer and recovery tests, then relevant existing
  backend tests, frontend tests, build and contract checks.
- Run export/dry-run/import/reconcile on the complete preserved dataset; verify
  selected local password logins without printing credentials.
- Interrupt and resume a nonempty multi-batch import, including commit/checkpoint
  crash boundaries, changed targets, duplicate keys and malformed source bundles.
- Repeat into a fresh target and compare deterministic domain documents.
- Compare every report filter and ordering/collation against PostgreSQL fixtures.
- Measure representative/larger datasets and all domain write paths; inspect plans
  and decide indexes/pagination from evidence.
- Back up, restore into another target and verify fingerprints and application flows.
- Rehearse PostgreSQL restore and write-free rollback with the original revision.
- Run original-source/device-database preservation checks and record acceptance.

The preserved-data gates passed and Phase 11 activated `learnova`. Live payment
capture and browser click acceptance were not performed. The volume fixture's
quiz remains locked by the preserved lesson-access rule, so its quiz timing is
explicitly recorded as unmeasured rather than bypassing that rule.
