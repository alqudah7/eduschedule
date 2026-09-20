# EduSchedule ops runbook

This file is what you follow at 2am. Everything else is context.

Related refs:
- `AUDIT.md` — full project findings
- `MULTITENANT.md` — multi-tenancy architecture
- `ops/backup.sh` — pg_dump backup script (uses cross-version-compatible `psql \copy` in practice)
- `.github/workflows/db-backup.yml` — scheduled backup workflow

---

## 1. Database roles — who does what

Two credentials, two purposes. Do not blur them.

| Purpose | Role | Where it lives | What it can do |
|---|---|---|---|
| App runtime | `eduschedule_app` | Railway env: `DATABASE_URL` on `eduschedule-api` | `SELECT/INSERT/UPDATE/DELETE` on the 12 application tables + `USAGE, SELECT` on sequences + `EXECUTE` on `find_user_for_login`. Nothing else. `NOSUPERUSER`, `NOBYPASSRLS`. RLS actively enforces. |
| Migrations / ops | `postgres` (Railway default superuser) | Railway env: `MIGRATE_DATABASE_URL` on `eduschedule-api`; local `MIGRATE_DATABASE_URL` when running `alembic` from a laptop | Full DDL: create tables, create/alter roles, replace functions. RLS is bypassed for this role, which is fine because it never serves user traffic. |

**Never share the superuser credential with the app.** It exists so Alembic can do DDL. If you find yourself using it from anywhere that handles user requests, stop and reconsider.

Verify at any time:
```bash
psql "$DATABASE_URL" -c "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
# Both must be false when the app is querying.
```

If either is `t`, the app is running as a superuser and RLS is off. That is a P0.

---

## 2. Backup

### Where backups live

- Automated GitHub Actions workflow: `.github/workflows/db-backup.yml` — runs `ops/backup.sh` on schedule; uploads to the workflow run's artifacts.
- Ad-hoc local dumps written to `~/eduschedule-backups/YYYY-MM-DD/prod-<UTC-timestamp>/`.
- Both use `psql \copy` per table (CSV) because production runs Postgres 18 and pg_dump requires the client to be at least the server's major version — CSV via `\copy` is version-independent.

### Take a fresh backup by hand

```bash
export RAILWAY_TOKEN='...'
# Fetch the current DATABASE_PUBLIC_URL from the Postgres service
railway variables --service Postgres --json \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['DATABASE_PUBLIC_URL'])" \
    > /tmp/prod_db_url

# Run the script — it dumps to CSV per table
export DATABASE_URL="$(cat /tmp/prod_db_url)"
BACKUP_DIR=~/eduschedule-backups/$(date -u +%Y-%m-%d) bash ops/backup.sh
```

The dump is a directory of `<TableName>.csv` files plus `tables.txt` listing them.

---

## 3. Restore from backup

**Test the restore quarterly** against a scratch database. An untested backup is not a backup.

### Prepare a target database

Fresh Railway Postgres (or local for a dry-run):

```bash
# 1. Provision an empty Postgres.
# 2. Point $MIGRATE_DATABASE_URL at it as a superuser.
export MIGRATE_DATABASE_URL='postgresql://postgres:...@host/dbname'
export DATABASE_URL="$MIGRATE_DATABASE_URL"   # local dev; prod separates them
```

### Rebuild the schema with Alembic

```bash
cd backend
JWT_SECRET=doesnt-matter-for-migrations venv/bin/alembic upgrade head
```

This runs every revision from empty:
1. `21b21e11f5af` baseline — creates pre-tenancy tables (`User`, `Teacher`, `Lesson`, `Duty`, `Substitution`, `Alert`, `Absence`, `AuditLog`, `teacher_attendance`)
2. `ac08810385eb` — creates `organizations`, `schools`, `school_settings`
3. `e2132b03e429` — seeds `D3 Consultants` + Al Hekma school + school_settings
4. `c3f705ecdedf` → `887d83a51971` → `3fb5bc61c3cb` — add nullable `school_id`, backfill, set NOT NULL
5. `fa4c92e951a6` — composite indexes
6. `8878824788ec` — per-school unique constraints
7. `3f196deaec55` — enable RLS + tenant_isolation policy
8. `28c532490174` — `Substitution.dutyId` unique becomes `(school_id, dutyId)`
9. `12ce483c979f` — hardened `find_user_for_login` SECURITY DEFINER function

At this point the schema is complete and Al Hekma exists as a row, but the tenant tables are empty.

### Provision the app role

The migration chain does not create the `eduschedule_app` role — role management is a superuser operation that lives with ops.

```sql
-- Connect as superuser
CREATE ROLE eduschedule_app
    WITH LOGIN PASSWORD :'app_pw'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS NOINHERIT;

GRANT CONNECT ON DATABASE :"dbname" TO eduschedule_app;
GRANT USAGE ON SCHEMA public TO eduschedule_app;

GRANT SELECT, INSERT, UPDATE, DELETE ON
    "User", "Teacher", "Lesson", "Duty", "Substitution",
    "Alert", "Absence", "AuditLog", teacher_attendance,
    organizations, schools, school_settings
    TO eduschedule_app;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO eduschedule_app;

-- Re-run the migration to attach the EXECUTE grant on find_user_for_login
-- (its GRANT is conditional on the role existing).
```

Then re-run `alembic upgrade head` — revision `12ce483c979f` idempotently attaches `GRANT EXECUTE` now that the role exists.

Verify:
```sql
SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'eduschedule_app';
-- Both must be f, f.

SELECT grantee, privilege_type
FROM information_schema.routine_privileges
WHERE routine_name = 'find_user_for_login';
-- Should include eduschedule_app EXECUTE.
```

### Load the CSV data

```bash
# Assume backup dir is ~/eduschedule-backups/YYYY-MM-DD/prod-...
export BACKUP=~/eduschedule-backups/2026-09-20/prod-20260920T082441Z

# Order matters — FKs. Load parents before children.
psql "$MIGRATE_DATABASE_URL" <<SQL
-- Bootstrap organizations/schools/school_settings were seeded by the migration,
-- so skip those. Load application rows in FK order:
\copy "User"               FROM '$BACKUP/User.csv'               CSV HEADER
\copy "Teacher"            FROM '$BACKUP/Teacher.csv'            CSV HEADER
\copy "Duty"               FROM '$BACKUP/Duty.csv'               CSV HEADER
\copy "Lesson"             FROM '$BACKUP/Lesson.csv'             CSV HEADER
\copy "Substitution"       FROM '$BACKUP/Substitution.csv'       CSV HEADER
\copy "Alert"              FROM '$BACKUP/Alert.csv'              CSV HEADER
\copy "Absence"            FROM '$BACKUP/Absence.csv'            CSV HEADER
\copy "AuditLog"           FROM '$BACKUP/AuditLog.csv'           CSV HEADER
\copy teacher_attendance   FROM '$BACKUP/teacher_attendance.csv' CSV HEADER
SQL
```

### Verify the restore

Dry-run first — restore into a **scratch** database, sanity check a few rows, then promote:

```sql
SELECT count(*) FROM "Teacher";   -- should match backup
SELECT count(*) FROM "Lesson";    -- should match backup
SELECT name, status FROM "Teacher" WHERE name ILIKE '%adreen%';
```

Then switch the app's `DATABASE_URL` to point at the restored database. Redeploy if not automatic.

### Restore procedure has NOT been dry-run yet

The last recorded dry-run was zero. Do one this quarter. Set a calendar reminder.

---

## 4. Add a second tenant (school)

Phase 3 (subdomains, self-serve onboarding) is not shipped yet — until then, adding a school is an ops action, not a product feature. Do NOT do this casually: **once a second school exists, any code path that relies on RLS being the only isolation layer is exposed** if a bug or misconfig disables RLS.

### Prerequisites

- Confirm RLS is currently enforcing (see §1). If `rolsuper` or `rolbypassrls` is true for the app role, stop.
- Take a fresh backup before starting (see §2).
- Have the customer's organization and school details ready:
  - Organization name + slug
  - School name + slug + timezone (IANA, e.g. `Asia/Bahrain`) + locale + working days + periods + breaks

### Steps

Run as the **superuser** (`MIGRATE_DATABASE_URL`), not the app role.

```sql
-- 1. Insert the organization
INSERT INTO organizations (name, slug, country, plan, status)
VALUES ('New Org', 'new-org', 'BH', 'TRIAL', 'ACTIVE')
RETURNING id;
-- Note the returned org_id.

-- 2. Insert the school
INSERT INTO schools (
    organization_id, name, slug, country, timezone,
    locale_default, status
)
VALUES (
    <org_id>, 'New School', 'newschool', 'BH', 'Asia/Bahrain',
    'EN', 'ACTIVE'
)
RETURNING id;
-- Note the returned school_id.

-- 3. Seed the school's settings
INSERT INTO school_settings (
    school_id, working_days, school_levels, supported_locales,
    periods, breaks, features_enabled
)
VALUES (
    <school_id>,
    ARRAY['SUN','MON','TUE','WED','THU'],       -- adjust per school
    ARRAY['ELEMENTARY','MIDDLE','HIGH'],         -- adjust per school
    ARRAY['EN'],
    '[{"number":1,"label":"Period 1","start":"08:00","end":"08:45"}]'::jsonb,
    '[]'::jsonb,
    '{}'::jsonb
);

-- 4. Create the school's first admin user
INSERT INTO "User" (id, email, password, name, role, school_id)
VALUES (
    'user-' || substr(md5(random()::text), 1, 24),
    'admin@newschool.com',
    -- bcrypt-hash the temporary password out of band; DO NOT paste
    -- plaintext into psql. Use: python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('...'))"
    '$2b$12$...',
    'Admin',
    'ADMIN',
    <school_id>
);
```

### Update the login endpoint

**This is the currently-unsafe part.** The login endpoint pins `school_id = 1` (Al Hekma) — see `backend/app/routers/auth.py::_LOGIN_SCHOOL_ID`. Until Phase 3 wires subdomain resolution, a second school's users **cannot log in** with the current code.

Options:
- Ship the second school AFTER Phase 3 (recommended).
- Or manually change `_LOGIN_SCHOOL_ID` to a resolver that reads a subdomain now (~half day of work).

Do not extend the current `_school_slug` form field back into the request — that reopens the enumeration + cross-tenant auth vectors that were closed this quarter.

### Verify isolation

```sql
-- As the app role, School A's admin logs in (school_id=1).
-- With their token, GET /api/teachers/ must return only school 1's teachers.
-- Repeat as School B's admin (school_id=2) — must return only school 2's.

-- At the DB level:
SET ROLE eduschedule_app;
SET app.current_school_id = '1';
SELECT count(*) FROM "Teacher";   -- School A only.
SET app.current_school_id = '2';
SELECT count(*) FROM "Teacher";   -- School B only.
```

---

## 5. Common ops actions

### Run migrations against production

Never run migrations from a container that serves user traffic. Do it from a workstation:

```bash
export RAILWAY_TOKEN='...'
railway variables --service Postgres --json | \
    python3 -c "import json,sys; print(json.load(sys.stdin)['DATABASE_PUBLIC_URL'])" \
    > /tmp/prod_db_url

cd backend
export MIGRATE_DATABASE_URL="$(cat /tmp/prod_db_url)"
export DATABASE_URL="$MIGRATE_DATABASE_URL"    # env.py falls back to this
export JWT_SECRET=doesnt-matter

venv/bin/alembic current
venv/bin/alembic upgrade head        # or `upgrade +1` for cautious step
```

### Rotate the app-role password

```sql
-- As superuser:
ALTER ROLE eduschedule_app WITH PASSWORD :'new_pw';
```

Then set the new URL on Railway:

```bash
railway variables --service eduschedule-api \
    --set "DATABASE_URL=postgresql://eduschedule_app:<new_pw>@postgres.railway.internal:5432/railway"
```

That triggers a redeploy. Watch `/health` and confirm login works before you close the ticket.

### Emergency: RLS mis-firing so nobody can log in

Symptoms: every endpoint returns 401 or empty data.

Diagnose:
```sql
-- Under the app role, no GUC set:
SET ROLE eduschedule_app;
SELECT count(*) FROM "User";        -- expect 0 (RLS blocks — normal)
SET app.current_school_id = '1';
SELECT count(*) FROM "User";        -- expect the real count (RLS lets Al Hekma through)
```

If the second query still returns 0, either the policy is broken (check `SELECT * FROM pg_policies`) or `school_id = 1` isn't populated (`SELECT count(*) FROM "User" WHERE school_id IS NULL`).

Nuke option (temporary, until fix): grant `BYPASSRLS` to the app role. **This disables tenant isolation until you undo it.** Only use if the site is down and you need to unblock traffic.

```sql
ALTER ROLE eduschedule_app WITH BYPASSRLS;
-- ...fix the underlying problem...
ALTER ROLE eduschedule_app WITH NOBYPASSRLS;
```

---

## 6. Known-unfixed items you should know before making changes

Straight from `AUDIT.md` and prior sessions:

- 74 of 75 tenant-table queries in the router layer lack an explicit `.filter(Model.school_id == ...)` — they depend on RLS. If RLS is disabled (see the nuke option above), every one of those queries leaks.
- `main.py::seed_database` contains `Admin@123` and `Teacher@123` in plaintext. `ENV=production` gates the endpoint. The strings are still in the source.
- The 72 pre-existing teacher accounts still have `Teacher@123` as their password.
- Historical secrets (`SEED_KEY`, admin+teacher default passwords) remain in `alqudah7/eduschedule` git history.
- 115 Dependabot vulnerabilities. `python-jose` and `passlib` are the highest-priority to migrate off.

Fix or accept — but don't be surprised.
