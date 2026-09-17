# EduSchedule — Teacher Scheduling Platform

A B2B SaaS web application for schools to manage teacher duty assignments,
substitutions, and conflict detection.

## Tech Stack
- **Frontend**: Next.js 16, TypeScript, Tailwind CSS v4, TanStack Query v5, Framer Motion, Recharts
- **Backend**: FastAPI (Python 3.11), SQLAlchemy, PostgreSQL
- **ORM**: SQLAlchemy owns the runtime schema. A dormant Prisma schema and
  seed script remain in `frontend/prisma/` but are hard-gated against
  production and scheduled for removal (see AUDIT.md).
- **Auth**: JWT tokens stored in localStorage

## Prerequisites
- Node.js 20+ and npm
- Python 3.11+
- PostgreSQL 15+

## Quick Start

### 1. Create database
```bash
createdb eduschedule
```

### 2. Backend setup
```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set DATABASE_URL=postgresql://user:password@localhost:5432/eduschedule
#             set JWT_SECRET=your-super-secret-key
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend setup
```bash
cd frontend
npm install
cp .env.local.example .env.local
# Edit .env.local: set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

### 4. Seed the database (non-production only)
The backend exposes a bootstrap endpoint that populates demo data if the
database is empty. It refuses to run when `ENV=production`.
```bash
curl -X POST http://localhost:8000/api/admin/seed
```

### 5. Login
- URL: http://localhost:3000
- Email: **admin@eduschedule.com**
- Password: whatever the seed set. Change it on first login.

## API Docs
- Swagger UI: http://localhost:8000/docs

## Deploy

### Frontend (Vercel)
```bash
cd frontend && vercel --prod
```

### Backend (Railway)
```bash
cd backend && railway up
```

## Database backups

Two independent layers guard against the DB-wipe scenario documented in
AUDIT.md.

### Layer 1 — Railway native snapshot backups (primary)

In the Railway dashboard: **Postgres service → Backups**. Enable and set a
retention window that matches your recovery needs. Railway backups are
crash-consistent snapshots and are the fastest path to restore. Availability
depends on the plan tier.

### Layer 2 — pg_dump via GitHub Actions (fallback, works on any plan)

`.github/workflows/db-backup.yml` runs daily at 03:00 UTC and produces a
gzipped `pg_dump` artifact retained for 30 days. This gives an off-provider
copy independent of Railway.

**Enabling the workflow (one-time):**

1. In Railway dashboard → Postgres → Connect → copy the `DATABASE_URL`.
2. In GitHub: repo **Settings → Secrets and variables → Actions → New
   repository secret**. Name it `RAILWAY_DATABASE_URL`, paste the URL.
3. On the Actions tab open **Database backup → Run workflow** to verify.
4. Download the artifact from the run and confirm it opens with
   `gunzip -t`.

For local runs the same script works standalone:
```bash
DATABASE_URL='postgresql://...' ./ops/backup.sh
```

### Restore procedure

> **Test the restore quarterly.** An untested backup is not a backup. Set
> a calendar reminder to run the "dry-run into a scratch database" flow
> below and verify a few known rows before you rely on it.

**From a Railway snapshot:**

1. Railway dashboard → Postgres service → Backups → pick a snapshot →
   **Restore**. Railway creates a new Postgres service from the snapshot.
2. Copy the new service's `DATABASE_URL`.
3. In the `eduschedule-api` service → Variables → replace `DATABASE_URL`
   with the new value. The service redeploys and reads from the restored
   DB.
4. Once verified, decommission the old Postgres service (see AUDIT.md on
   the "three Postgres services" cleanup).

**From a pg_dump artifact:**

```bash
# 1. Download the artifact from the Actions run you want to restore.
#    Unzip → you get eduschedule-20260917T030000Z.sql.gz

# 2. Dry-run into a local scratch database first — never restore straight
#    into prod:
createdb scratch
gunzip -c eduschedule-20260917T030000Z.sql.gz | psql scratch
psql scratch -c 'SELECT count(*) FROM "Teacher";'   # sanity check
dropdb scratch

# 3. If the dry-run succeeded, provision a fresh Railway Postgres, then:
export DATABASE_URL='postgresql://...fresh-service-url...'
gunzip -c eduschedule-20260917T030000Z.sql.gz | psql "$DATABASE_URL"

# 4. Point the API at the restored DB by updating DATABASE_URL in the
#    Railway service Variables tab.
```

## Features
- Teacher profile management with duty load tracking
- Weekly schedule grid with color-coded conflict visualization
- Automatic conflict detection on every duty save
- Fairness-engine ranked substitute suggestions (by workload %)
- Substitution request workflow with email notifications
- Severity-tiered alert system (Critical → Info)
- Reports: workload analytics, absence trends, full audit trail, CSV export

## Logo
Replace `{/* LOGO PLACEHOLDER — expects ~120px wide × 32px tall asset */}` in
`frontend/components/layout/Sidebar.tsx` with your `<Image>` component.

## Project Structure
```
eduschedule/
├── frontend/          # Next.js 16 app
│   ├── app/           # App Router pages
│   ├── components/    # UI + layout components
│   ├── lib/           # Types, API client, hooks
│   └── prisma/        # Schema + migrations + seed
└── backend/           # FastAPI app
    └── app/
        ├── models/    # SQLAlchemy models
        ├── schemas/   # Pydantic schemas
        ├── routers/   # API endpoints
        └── services/  # Business logic engines
```
