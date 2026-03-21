# backend/db/README.md

## Purpose
This folder contains the PostgreSQL bootstrap assets for Learnova:
- a full snapshot schema
- ordered migrations
- demo seed data

## Files

```plaintext
backend/db/
|- schema.sql
|- seed.sql
`- migrations/
   |- 001_extensions_and_enums.sql
   |- 002_core_entities.sql
   `- 003_learning_progress_and_reviews.sql
```

## PostgreSQL Assumption
This setup assumes:
- PostgreSQL
- `psql` is available in the terminal

## 1. Create Database

```bash
psql -U postgres -c "CREATE DATABASE learnova;"
```

If the database already exists, PostgreSQL will return an error and you can ignore that.

## 2. Run Ordered Migrations

```bash
psql -U postgres -d learnova -f backend/db/migrations/001_extensions_and_enums.sql
psql -U postgres -d learnova -f backend/db/migrations/002_core_entities.sql
psql -U postgres -d learnova -f backend/db/migrations/003_learning_progress_and_reviews.sql
```

## 3. Seed Demo Data

```bash
psql -U postgres -d learnova -f backend/db/seed.sql
```

## 4. Alternative: Apply Full Snapshot

If you want to bootstrap the DB in one shot instead of migrations:

```bash
psql -U postgres -d learnova -f backend/db/schema.sql
psql -U postgres -d learnova -f backend/db/seed.sql
```

## 5. Windows PowerShell Example

```powershell
psql -U postgres -c "CREATE DATABASE learnova;"
psql -U postgres -d learnova -f backend/db/migrations/001_extensions_and_enums.sql
psql -U postgres -d learnova -f backend/db/migrations/002_core_entities.sql
psql -U postgres -d learnova -f backend/db/migrations/003_learning_progress_and_reviews.sql
psql -U postgres -d learnova -f backend/db/seed.sql
```

## 6. Notes

- `schema.sql` is the full consolidated snapshot
- `migrations/` is the preferred incremental setup path
- `seed.sql` is demo-friendly and idempotent enough for repeated local setup
- the schema includes slug support so DB records map cleanly to frontend routes
