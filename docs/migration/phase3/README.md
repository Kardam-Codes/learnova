# Phase 3: authentication and user identity

MongoDB authentication is implemented behind an explicit authentication-store selector
and verified against the real local replica set. The current app's store selection has
not been changed. The decision about activating MongoDB during the remaining phases is
pending; there is no temporary PostgreSQL/MongoDB identity bridge.

## Why activation is separate

Course/enrollment/progress/payment/admin services still use PostgreSQL user references.
A new MongoDB-only user would not have the corresponding PostgreSQL row and could fail
those foreign-key writes. Existing imported UUIDs can use existing references, as the
rehearsal proves, but that does not make new accounts safe across mixed storage.

The user was asked whether to retain PostgreSQL operation while MongoDB is tested in
isolation, or activate MongoDB with a temporary identity bridge. Until answered, the
existing app selection stays unchanged. Full cutover remains Phase 11 after all modules
and existing data are ready. Do not set `AUTH_STORAGE=mongo` in the working app merely
to test this phase, or introduce unsynchronized dual writes.

## Implementation

- `backend/modules/auth/mongo_service.py`: MongoDB registration, availability, local login,
  Google login/profile update, and user lookup.
- `backend/modules/auth/storage.py`: one auth-store choice per application process.
- `backend/modules/auth/service.py`: existing PostgreSQL implementation retained for
  the working app and baseline comparison, including the shared Google verifier.
- Auth router/current-user dependency: selects the configured store through FastAPI
  dependency injection; role authorization still reads the persisted user role.
- `backend/db/mongo/bootstrap.py`: explicit bootstrap preparation/finalization for
  quiescent setup/import. `python -m backend.db.mongo.init_db` now also runs this step.

`AUTH_STORAGE` accepts `postgres` and `mongo`; its default preserves the existing
PostgreSQL behavior. Selection is frozen for the FastAPI lifespan and requires restart
to change. MongoDB failure returns JSON 503 and never falls back to PostgreSQL. Existing
course routes remain PostgreSQL-backed regardless of this auth selector.

The existing MongoDB process client is reused. No MongoDB auth operation opens a
PostgreSQL connection. MongoDB mode checks the applied schema version/checksum and
fixed bootstrap record before accepting auth requests. `/mongo/health` also includes
this auth setup check when that mode is selected. `/db/health` still checks PostgreSQL
and the configured MongoDB target because both are needed by the partially converted app.

## Compatibility and preserved behavior

- Existing endpoints, operation IDs, request/response models, successful statuses,
  `access_token`, `token_type`, and public user fields are preserved.
- Public user `id` maps to the same MongoDB UUID `_id`. Hashes, Google IDs, schema fields,
  and MongoDB storage identifiers are excluded from auth responses.
- New email creation and all lookups consistently trim and lowercase email.
- Existing PBKDF2 password hashes and token signing/expiry helpers are reused.
- Stored `super_admin` signs in through the admin role choice and retains its stored role.
- Wrong passwords/providers return 401; wrong role choice 403; missing user 404;
  duplicate email/provider identity 409; invalid request bodies remain readable 422.
- The persisted user role, rather than a stale/forged role claim, controls protected routes.
- Malformed signed token payloads that raise `TypeError` now produce 401 rather than 500.

The previous app permits login for an account whose `is_active` flag is false. This phase
preserves that behavior and the returned flag; changing account-disable policy is a
separate feature. Likewise, the existing signup role choices, including admin, are not
silently restricted by this storage migration.

Google credentials still use the existing verification helper, audience/email verification,
network timeout, and local-account conflict behavior. Verification happens once before
the retryable database transaction. Existing email-matched Google profiles keep their UUID
and creation date while updating name/provider identity as before. A Google identity already
stored with a different email returns a controlled 409 rather than creating another user
or silently merging accounts. Account/email reassociation is not a new feature in this phase.

Tests control Google responses and network failures; no live Google sign-in is claimed.

## Atomic bootstrap, imports, and retries

The fixed `app_metadata._id = auth_bootstrap` record must exist before registration.
An empty initialized target has `claimed=false`. First signup conditionally claims that
record and inserts its user in the **same** session transaction; only that signup receives
the automatic `super_admin` role. Other concurrent signups receive their selected role.
The unique email/Google indexes independently prevent duplicate identities.

PyMongo transaction retries reuse the same generated UUID, timestamp, and password hash;
external Google verification and token generation are outside the retryable callback.
An overall database deadline bounds retry execution. Tokens are issued after commit.
An insertion/validation failure rolls back the bootstrap claim together with the user write.

After importing any existing users, run bootstrap finalization before traffic. It closes
bootstrap and records an existing super administrator, preferring that role over ordinary
admin accounts. It never reopens claimed state after users are deleted. An initialized-empty
target containing subsequently imported users is rejected until finalization closes bootstrap.
Registration does not auto-initialize or infer first-admin ownership from a user count.

Schema/auth initialization and imports must run without concurrent application signup or
import traffic. The runtime registration path is transactional; the setup/import finalizer
is an explicit offline operation. Later import tooling must keep traffic stopped until both
data import and bootstrap finalization are verified.

Demo seeding still requires an empty target; it accepts the unclaimed bootstrap record
created by setup, then inserts demo users and closes bootstrap in the same transaction.
It refuses previously claimed state or existing domain data.

## Verification commands

From the project root:

```powershell
# All infrastructure/auth tests; guarded disposable MongoDB databases only.
.\.venv\Scripts\python.exe -m pytest backend\tests -q --junitxml=.local\migration-baseline\phase3-all-tests.xml

# Rehearse all existing source identities in a temporary MongoDB database,
# then compare all saved API responses in both auth modes.
.\.venv\Scripts\python.exe -m backend.db.migration.verify_phase3_baseline

# Keep starting the working backend using its existing storage selection.
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

The integration suite covers registration/login/me, password/provider/role conflicts,
normalized email, missing/expired/tampered/malformed tokens, persisted-role authorization,
Google profile updates/collisions/verification failures, imported bootstrap state, local
and Google concurrent first signups, duplicate-email races, failed-insert rollback,
transient transaction retry, unavailable database redaction/CORS, no PostgreSQL fallback,
demo setup sequencing, and all Phase 2 infrastructure tests.

Verified on 2026-10-08: **74 tests passed** (37 authentication and 37 infrastructure),
with one upstream Starlette/AnyIO deprecation warning. The source rehearsal preserved
all six imported identities and **76/76 API responses in each auth mode**. PostgreSQL's
19 table fingerprints and schema remained unchanged; the temporary namespaces were removed.

The source rehearsal reads PostgreSQL in read-only transactions, copies six existing
identities into a disposable MongoDB namespace, preserves hashes/UUIDs/roles/provider
metadata/status/timestamps (with documented BSON millisecond precision), closes imported
bootstrap, and compares 76 saved API responses in each auth mode. It does not know or
request real users' plaintext passwords; migrated password login is exercised using a
known-password fixture with the existing hash format. Real imported subjects are exercised
through token/user lookup and protected read endpoints.

All 40 original OpenAPI operations and 27 schemas retain their contracts. Only the
`/auth/login` explanatory description was updated to describe the configured auth store;
the `/mongo/health` addition comes from Phase 2.

Private response fixtures, aggregate verification reports, and JUnit evidence remain under
ignored `.local/migration-baseline`. The source tables and pre-existing MongoDB databases
are not written by the rehearsal. Generated test databases are removed afterward.

## Handoff

Next is Phase 4 admin course/content/quiz persistence. Its MongoDB implementation should
reuse the lifecycle client, role dependency, UUID identities, validators, and test isolation.
The broader store-activation decision is pending; do not treat completed auth tests as a
production cutover. Git setup and the separate PostgreSQL restore/write rehearsal remain
open Phase 0 gates before cutover/release.

Official references: [PyMongo transactions and retry behavior](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/crud/transactions/),
[Google ID token verification](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token).
