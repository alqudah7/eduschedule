# EduSchedule — Teacher Scheduling Platform

A B2B SaaS web application for schools to manage teacher duty assignments,
substitutions, and conflict detection.

## Tech Stack
- **Frontend**: Next.js 16, TypeScript, Tailwind CSS v4, TanStack Query v5, Framer Motion, Recharts
- **Backend**: FastAPI (Python 3.11), SQLAlchemy, PostgreSQL
- **ORM**: Prisma 7 (frontend migrations) + SQLAlchemy (backend queries)
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
# Edit .env.local: set DATABASE_URL (same DB), NEXT_PUBLIC_API_URL=http://localhost:8000
npx prisma generate
npx prisma migrate dev --name init
npx prisma db seed
npm run dev
```

### 4. Login
- URL: http://localhost:3000
- Email: **admin@eduschedule.com**
- Password: **Admin@123**

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
