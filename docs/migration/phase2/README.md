# Phase 2: MongoDB infrastructure and verification

This phase prepares MongoDB for the later domain conversions. Authentication,
courses, quizzes, progress, reports, and payment routes still read/write PostgreSQL.
No PostgreSQL records have been imported into MongoDB yet.

## Deployment and versions

- Existing Windows service: `MongoDB`, automatic startup, same NetworkService account.
- Existing MongoDB Community Server: **8.3.7**, FCV 8.3, retained and tested.
- Replica set: **learnova-rs**, one member, `localhost:27017`.
- Original data directory and `127.0.0.1` binding are retained.
- This is a development deployment with transaction support and **no high availability**.
- Python: **3.12.10**, workspace `.venv`.
- PyMongo: **4.18.2**, pinned in backend runtime requirements.
- MongoDB Database Tools: **100.19.1**, portable tools under ignored `.local/tools`.
- pytest **8.4.2**, httpx **0.28.1**. Existing FastAPI/Pydantic/PostgreSQL dependency pins remain.
- `backend/requirements-dev.lock.txt` records every installed package version for reproduction.

Readiness is based on the tested combination, not on a claim that every installed
application is the newest release. The earlier version audit found newer MongoDB
server patches and Compass releases. This phase does not replace the server binary
or Compass: those updates are separate from enabling replication and should receive
their own backup, compatibility, and restart checks. mongosh is optional because
the checked-in setup tools use PyMongo commands directly.

## Running the backend

From the project root in PowerShell:

```powershell
# Recreate the verified development environment if necessary:
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.lock.txt

# Start the backend using this environment:
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

The previously installed global Python environment does not contain the new driver.
Use `.venv` for backend startup, tooling, and migration tests.

Local `.env` now contains these additional settings; existing credentials are retained:

```dotenv
MONGODB_URI=mongodb://localhost:27017/?replicaSet=learnova-rs
MONGODB_DB=learnova_migration_dev
MONGODB_TIMEOUT_MS=5000
```

The migration target is separate from existing databases on the service. Do not
point the setup commands at an existing application's database. PostgreSQL settings
remain necessary until the domain conversion and cutover phases finish.

## Client lifecycle and readiness

`backend/config/env.py` loads local settings independently of any database call;
process environment values retain precedence. `backend/config/db.py` delegates to
that loader so existing PostgreSQL tooling keeps working.

`backend/config/mongo.py` creates one synchronous PyMongo client per FastAPI process
in lifespan and closes it on shutdown. BSON dates decode with a UTC timezone. Server
selection, connection, socket, pool wait, and operation timeouts are finite. Startup
does not require an available database, allowing process liveness to be inspected.

- `/health`: process liveness, no database dependency.
- `/mongo/health`: ping plus replica-set/writable-primary check; useful during migration.
- `/db/health`: existing PostgreSQL response fields retained; when MongoDB is configured,
  an additive `mongodb` result also checks the migration target. Either unavailable
  dependency returns JSON HTTP 503 with a sanitized message.

An empty MongoDB development database passing readiness means the infrastructure
works. It does not mean domain routes have been migrated or production is ready.
When the PostgreSQL dependency is removed later, adjust combined readiness accordingly.

## Schema initialization

```powershell
.\.venv\Scripts\python.exe -m backend.db.mongo.init_db
```

The initializer consumes the frozen Phase 1 specification, creates its 16 collections
and 28 named indexes, and writes version/checksum information to `schema_migrations`.
The v1 SHA-256 is:

`8cc0040d337068cebb97642976d6b63f4a9f1d0927a5fafb6f36a19a335ffef8`

The command can be repeated. It permits only `learnova_migration_dev` and generated
`learnova_test_<32 lowercase hex digits>` names in Phase 2. A populated unversioned
database, unmanaged collection, changed validator/options, changed named index, or
changed migration checksum stops setup. It never drops indexes or silently changes
validators. DDL is not transactional: an interrupted empty initialization can be
repeated when its existing definitions still match. Concurrent setup invocations
are not supported; run setup as a single deployment step.

Actual validators enforce required fields, types, enums, schema versions, nested
document structure, paid-course pricing, and matching content modes. Optional unique
provider identifiers and submission keys use partial indexes and are omitted when
absent. Cross-document references and business rules still require the later services.

## Fixtures and integration tests

The deterministic fixture includes a super-admin, instructor, learner, free/paid
courses, video/document/image/quiz content, a quiz with nested options/reward rules,
tags, and closed bootstrap state. It is inserted transactionally into fresh test
databases. It is **not inserted into the persistent development target by default**.

An explicit empty-development-database demo command is available:

```powershell
.\.venv\Scripts\python.exe -m backend.db.mongo.seed --demo
```

Fixture emails use `@learnova.example`. Its publicly known password is
`LearnovaDemo!123`; these are disposable demo identities. The seed refuses populated
databases and never replaces existing accounts. Demo identities do not become
usable in current API auth until its MongoDB conversion in Phase 3.

Run the real-server integration suite:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q --junitxml=.local\migration-baseline\phase2-tests.xml
```

Tests require a running writable replica set; they fail rather than silently skip if
it is absent. `MONGODB_TEST_URI` may override the local URI. Each database fixture
generates a fresh UUID name, checks it is absent and distinct from the application
database, and cleans up only that exact name. Never point tests at a shared remote
deployment without reviewing its access and intended test use.

Coverage includes all collection validators rejecting incomplete records, repeatable
initialization, schema/index/checksum drift, refusal to adopt unversioned data,
email/provider/payment/retry-key uniqueness, absent-vs-null identifiers, integer money,
cross-field rules, UTC dates, seed safety, client shutdown, readiness failure/redaction,
environment loading, and real multi-document commit/rollback after an invalid write.

Verified on 2026-10-08: **37 tests passed**. One upstream Starlette/AnyIO
deprecation warning remains; it does not affect these results. All 76 saved API
responses preserve their existing fields and values, with the documented additive
MongoDB readiness field. The 19 PostgreSQL table fingerprints and schema match the
original baseline. All 40 original OpenAPI operations and 27 schemas are unchanged;
`/mongo/health` is one additive operation. No temporary test databases remain.

## Backups, conversion, and recovery evidence

Private artifacts are ignored under `.local/migration-baseline`:

- `mongo-20261008T062832Z/mongodb.archive.gz`: consistent logical backup before conversion.
- Original/proposed MongoDB config, SHA-256 manifest, source fingerprints, dump/restore logs.
- `restore-verification.json`: each of three user databases restored into a fresh temporary
  namespace, matched by record count and BSON digest, then removed.
- `phase2-application.original.env`: private pre-change application settings.
- `phase2-tests.xml`, `phase2-baseline-verification.json`, and the Phase 2 report.
- Original PostgreSQL run's `phase2-api-baseline.json`: private regression responses.

Backup uses a short `fsync` write lock with `fsyncUnlock` in a `finally` block. It
captures a complete logical archive (MongoDB tools exclude the internal `local`
replication database); record-level restore verification covers user databases.
Service conversion verifies archive/config hashes and uses Windows administrator
privileges to write the configuration and restart the service. Initial attempts
without Windows elevation were denied before a configuration change; the elevated
invocation succeeded. Existing database fingerprints matched after conversion and
after restore rehearsal. The setup scripts intentionally refuse to overwrite an
already configured, different replica set.

Recovery at this infrastructure-only stage:

1. Stop backend processes using this target.
2. Review the saved original config and current config. In an administrator PowerShell,
   restore `mongod.original.cfg` to the service's configuration path and restart `MongoDB`.
   The data directory stays in place; do not delete databases or replication files.
3. Remove the three MongoDB settings added to `.env`, or compare against the private
   pre-change copy. Preserve any application credentials changed since the backup.
4. Restart the backend using `.venv`; `/db/health` then checks PostgreSQL alone.
5. If recovering actual data loss, restore first into a new namespace and verify it
   before planning any replacement. Do not run a blanket `mongorestore --drop`.

The saved source archive is additional code recovery evidence; review local changes
before restoring any files. No cutover or source-data deletion has happened.

## Handoff and open gates

Phase 3 can now implement MongoDB authentication using these validators, unique indexes,
the lifecycle client, and isolated tests. Imported data and access preservation remain
mandatory. The development target currently contains schema metadata, not migrated users.

Phase 0 is still incomplete: the intended Git repository and permission to create a
separate PostgreSQL restore/write-test database remain unresolved. MongoDB backup restore
verification does not satisfy the separate PostgreSQL recovery gate. Resolve those before
cutover or release. This phase stops before authentication implementation.

## Official references

- [Standalone-to-replica-set conversion](https://www.mongodb.com/docs/manual/tutorial/convert-standalone-to-replica-set/)
- [PyMongo 4.18.2 package and Python compatibility](https://pypi.org/project/pymongo/4.18.2/)
- [MongoDB Database Tools downloads](https://www.mongodb.com/try/download/database-tools/releases/archive)
- [PyMongo transactions](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/crud/transactions/)
- [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/)
