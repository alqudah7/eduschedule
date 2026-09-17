# EduSchedule audit — 2026-09-17

Full-project audit produced by five parallel investigations (data layer,
reliability, feature completeness, security, code quality), then deduplicated
and cross-checked. All findings cite `file:line` evidence.

## TL;DR

- **Substitutions "No lessons on Tuesday" bug**: fixed in commit `27822f6`.
  Root cause: DB stores canonical `TUE`, dropdown was sending `Tuesday`. Now
  routed through a single `app.utils.days.normalize_day` helper.
- **Previous DB-wipe root cause: identified.** See "DB-wipe forensics" below.
- **20 Critical / 30 Important / 22 Nice-to-have findings.**
- **Two Part-2 assumptions were wrong** — see "Part 2 corrections" below.
- **One regression introduced by the fix commit** — see Critical #17.

## Part 2 corrections (things you thought were missing but exist)

1. **Bulk teacher CSV import already exists.** `POST /api/teachers/bulk-import`
   at `backend/app/routers/teachers.py:94` accepts `full_name, email, subject,
   phone, school_level` — the exact fields you asked for. What's missing is a
   button on the Teachers page (currently only reachable via Schedule → Import).
   The endpoint **does** have a Critical bug though — it hardcodes
   `Teacher@123` as the default password (Critical #7).

2. **Schedule CSV import already reports per-row errors.**
   `backend/app/routers/schedule.py:132-148` returns `{"row": n, "reason":
   "Teacher '<email>' not found — import teachers first"}` per row and
   continues. Nothing "fails silently" server-side. What's missing is the
   frontend actually rendering `result.errors` (verified: the schedule page
   never displays the errors array).

## DB-wipe forensics

The most likely path for the previous wipe, ranked by likelihood:

**Path 1 — `SEED_KEY` in the repo.** `backend/app/config.py:15` sets a default
of `"eduschedule-seed-2026"`; `backend/render.yaml:15` commits the same value.
The key was public. `POST /api/admin/seed?force=true` (`backend/app/main.py:141-149`)
then does `db.query(AuditLog).delete()` … `db.query(User).delete()` on **8
tables in one transaction** — no audit row, no snapshot, no confirmation.
Anyone with the repo and the public URL could wipe prod in one HTTP call.

**Path 2 — Prisma seed.** `frontend/prisma/seed.ts:21-28` runs `deleteMany()`
on 8 tables against `DATABASE_URL`. `frontend/package.json` has `prisma
generate` in both `postinstall` and `build` scripts — a `prisma migrate deploy`
or `prisma db seed` from any developer machine pointed at the live URL wipes
prod. Prisma is otherwise dead (verified: zero imports outside `seed.ts`;
`PrismaClient` never instantiated in the frontend runtime).

**Path 3 — Wrong Postgres.** The Railway project has **three Postgres
services** (`Postgres`, `Postgres-CQHJ`, `Postgres-Srdl`). Only the main one
is authoritative. A past deploy could have connected to the wrong one and
been mistaken for "wiped".

**Silent failure amplifier.** Startup wraps everything in `except Exception:
pass` (`main.py:42-43` and `main.py:66-72`). A broken migration, silent
`NameError` on `_sync_teacher_profiles_from_lessons` (Critical #10), or
partial schema update all deploy invisibly, so damage isn't noticed until a
user complains.

---

## Findings

### 🚨 Critical

1. **`SEED_KEY` hardcoded in the repo.** Default `"eduschedule-seed-2026"` in
   `backend/app/config.py:15` and committed to `backend/render.yaml:15`.
   → Delete the default; refuse to boot without the env var; rotate now.

2. **`/api/admin/seed?force=true` deletes 8 tables in one call.**
   `backend/app/main.py:141-149`. No audit, no snapshot, no confirmation.
   → Remove the `force=True` branch; move seeding to a manual script that
   requires `CONFIRM=<db-name>` and refuses to run in production.

3. **`/api/admin/debug-login` accepts email + password as query params,
   unauthenticated, and returns bcrypt tracebacks.** `main.py:93-116`.
   Passwords in URLs get written to Railway/Render/CDN access logs.
   → Delete this endpoint today.

4. **`/api/admin/debug-auth` returns stack traces unauthenticated.**
   `main.py:80-90`. Comment already says "Remove after debugging".
   → Delete.

5. **`require_admin` is defined but never used.** `backend/app/middleware/auth.py:53`
   is imported nowhere. Every authenticated `TEACHER` can create/delete other
   teachers (`teachers.py:57,199,217`), bulk-import (`teachers.py:94`), import
   schedules (`schedule.py:114`), create/delete duties (`duties.py:89,132,156`),
   assign substitutes (`substitutions.py:163`), and mark any teacher absent
   (`teachers.py:231`).
   → Add `Depends(require_admin)` to every mutation and privileged read.

6. **Default admin credentials `admin@eduschedule.com` / `Admin@123` published
   in the repo.** `README.md:51`, `frontend/app/(auth)/login/page.tsx:76`,
   `backend/app/main.py:154`, `frontend/prisma/seed.ts:16`. Combined with #2
   this is a well-known way in.
   → Force password reset on first login; remove from README and login UI.

7. **Default password `Teacher@123` on bulk teacher import.**
   `backend/app/routers/teachers.py:134` sets every imported teacher's password
   to this literal; `backend/app/schemas/teacher.py:16` makes it the default for
   `TeacherCreate.password`.
   → Generate a random temporary password per teacher; require reset on first
   login; drop the schema default (password becomes required).

8. **Seed writes long-form day names — force reseed re-breaks the day bug.**
   `backend/app/main.py:184` `days = ["SUNDAY", "MONDAY", ...]`. If anyone
   runs `/api/admin/seed?force=true` after your bug fix, the DB is filled with
   `"SUNDAY"` rows that the new `normalize_day` cannot match on read.
   → Change to canonical 3-letter form or push through `normalize_day`.

9. **Prisma is a dormant wipe vector.** `frontend/package.json:6-8` runs
   `prisma generate` on `postinstall` and `build`. The Prisma schema is
   4 migrations behind (missing `lessonId`, `schoolLevel`, `dutyCategory`,
   `TeacherAttendance`) and Prisma's `WeekDay` enum is `MON..FRI` while the
   live DB is `SUN..THU`. A stray `prisma migrate deploy` or `prisma db seed`
   corrupts prod. Prisma is otherwise unused at runtime (verified).
   → Delete `frontend/prisma/`; remove `@prisma/client`, `@prisma/adapter-pg`,
   `prisma`, `ts-node` from dependencies; drop `prisma generate` from build.

10. **`_sync_teacher_profiles_from_lessons()` is called but never defined.**
    `backend/app/main.py:41` invokes it; `grep` finds no definition anywhere.
    Silent `NameError` on every startup, swallowed by the outer `except`.
    Teacher profile sync has never actually run.
    → Either implement it (looks like it should aggregate `Lesson.subject`s
    and `Lesson.school_level` onto `Teacher.subjects` / `Teacher.school_level`)
    or delete the call.

11. **Startup swallows every exception silently.** `main.py:42-43` wraps the
    entire startup in `except Exception: pass`; `_run_column_migrations`
    (`main.py:66-72`) does the same per statement. A broken schema deploy is
    invisible.
    → Log with `logging.exception()`; let Railway fail the container so
    rollback triggers.

12. **Settings page in the sidebar but the route does not exist.**
    `frontend/components/layout/Sidebar.tsx:27` links `/settings`; no
    `frontend/app/(dashboard)/settings/page.tsx` exists → Next.js 404 on click.
    → Either ship a placeholder page or remove from `NAV_SYSTEM`.

13. **Duty delete has no confirmation.**
    `frontend/app/(dashboard)/duties/page.tsx:88` fires
    `onClick={() => deleteDuty.mutate(duty.id)}` immediately. One misclick =
    lost duty, no undo.
    → Add a `<ConfirmDialog>` before the mutation.

14. **CSV download URL leaks the JWT via `?token=`.**
    `frontend/app/(dashboard)/reports/page.tsx:22`. The token is written to
    Railway/CDN access logs and browser history.
    → Use a signed short-lived URL or fetch the blob and trigger download
    via `URL.createObjectURL`.

15. **Dashboard `SubRequestPanel` crashes on lesson-type subs (regression
    from commit `27822f6`).** `frontend/app/(dashboard)/dashboard/page.tsx:39-41`
    reads only `sub.duty.*`. Now that lesson-type subs exist, if the first
    pending sub is a lesson, `duty` is `null` and the time/location fields
    render `undefined–undefined`.
    → Branch on `sub.sub_type === 'lesson' ? sub.lesson : sub.duty`.

16. **No `isError` on 6 of 7 dashboard pages.** `dashboard`, `teachers`,
    `attendance`, `schedule`, `duties`, `alerts`, `reports` all handle
    `isLoading` but never `isError`. Backend down = silent empty pages.
    Only the fix commit's Substitutions Cover Classes panel does this.
    → Add a shared `<QueryError>` component; wire it into every consumer.

17. **No backup strategy anywhere.** No `pg_dump`, no Railway automated
    backups referenced, no restore playbook. Combined with the wipe vectors
    above this is a critical gap.
    → Enable Railway Postgres backups (paid tier), add a daily
    `pg_dump | gzip | rclone` cron to R2/S3, document restore in README.

18. **Three Postgres services in the Railway project.**
    `Postgres`, `Postgres-CQHJ`, `Postgres-Srdl` — only the main one is live.
    Orphans present risk of accidental cross-connection or wipe confusion.
    → Confirm the two extras hold nothing of value, then delete.

19. **`python-jose==3.3.0` has known algorithm-confusion CVEs (2024) and is
    effectively unmaintained.** `backend/requirements.txt:7`.
    → Migrate to `PyJWT >= 2.9`.

20. **No rate limiting anywhere.** `/api/auth/login`, `/api/admin/seed`, the
    debug endpoints, and `/api/admin/debug-login` are all open to brute force.
    → Add `slowapi` with tight buckets on `/auth/*` and `/admin/*`.

### ⚠️ Important

**Reliability & data integrity**

21. `_run_column_migrations` is ad-hoc runtime DDL, not Alembic. `alembic ==
    1.13.1` is in `requirements.txt:12` but no `alembic/` directory exists.
    Move to versioned revisions.
22. `/health` (`main.py:75-77`) returns `ok` unconditionally — doesn't touch
    the DB. Railway can't detect a broken connection. Add `SELECT 1`.
23. No DB connect retry loop. `database.py` creates the engine at import;
    briefly-unreachable DB at boot = every request 500s until manual restart.
24. `restartPolicyMaxRetries: 3` in `railway.json:9` combined with silent
    startup errors means a bad deploy sits dead. Raise + alert.
25. Axios interceptor at `frontend/lib/api.ts:20-23` forcibly redirects to
    `/login` on any 401 — even background polling. Add toast; skip redirect
    on background queries.
26. Prisma `WeekDay` enum is `MON..FRI` but live DB is `SUN..THU`
    (`frontend/prisma/schema.prisma:94`). Superseded by Critical #9 (delete
    Prisma).
27. `PRESCHOOL` silently coerced to `ALL`. `teachers.py:150` allow-list is
    `("ELEMENTARY","MIDDLE","HIGH","ALL")` — PRESCHOOL falls to else branch.
    But `substitutions.py:328-329` treats PRESCHOOL as first-class. Any
    PRESCHOOL teacher stored as ALL never matches the sub engine on level.
    → Add PRESCHOOL to the allow-list.
28. **Two competing attendance stores.** `Absence` model in
    `backend/app/models/alert.py:23` (`DATETIME date`, free-text `reason`)
    and `TeacherAttendance` in `backend/app/models/attendance.py:6`
    (`DATE date`, tri-state `status`). Reads of one miss the other. Pick one.
29. Substitution never sets `Duty.status = 'SUBSTITUTE_NEEDED'`. If any UI
    badges by duty status, duties needing subs look CONFIRMED.
30. Seed period times don't match the real bell schedule.
    `main.py:215` `lesson_slots = [("08:00","09:00"),…]`; real schedule is
    `07:40-08:30, 09:00-09:50, 09:50-10:40, 10:40-11:30, 11:50-12:40,
    12:40-13:30`. Move periods to `app.utils.periods`.
31. `Substitution.absentTeacherId` has no `ondelete` behaviour.
    `models/substitution.py:12`. Set explicit `RESTRICT` or `SET NULL`.
32. `Duty.updated_at` server default missing. `models/duty.py:20` has
    `onupdate` but no `server_default`. Rows inserted via raw SQL get NULL.
33. `Teacher.userId` in SQLA is nullable by default. `models/teacher.py:22`
    has no `nullable=False`. Prisma correctly marks it NOT NULL.

**Feature completeness (per-page issues)**

34. **Attendance "Mark All Present" fires N sequential mutations.**
    `attendance/page.tsx:114-118`. 60 teachers = 60 POSTs, partial-success
    risk. Add `POST /api/attendance/teachers/bulk`.
35. **Alerts "Resolve all" fires N sequential mutations.** `alerts/page.tsx:65`.
    Same pattern; add bulk endpoint.
36. **No teacher edit/delete UI.** `useUpdateTeacher` hook exists, `DELETE
    /api/teachers/{id}` route exists — no UI consumer.
37. **`duties/new/page.tsx:43` conflict detection is broken.**
    `conflictDetected = !!(… && schedule?.grid?.[watchedDay])` — checks the
    day-grid is non-empty, not that any lesson actually overlaps the time.
    False-positive every time the teacher has any lesson that day.
38. **"Export PDF" is `window.print()`.** `reports/page.tsx:106`. Prints
    the entire page including sidebar/topbar.
39. **Bulk-import UX mismatch.** Teacher import lives on the Schedule import
    modal, not the Teachers page. The primary flow ("import teachers first,
    then schedule") is inverted.
40. Backend routes with **zero frontend consumer**:
    - `POST /api/duties/{id}/resolve-conflict` (`duties.py:170`)
    - `POST /api/teachers/{id}/absent` (`teachers.py:231` — hook exists as
      `useMarkAbsent`, no button)
    - `DELETE /api/teachers/{id}` (`teachers.py:217`)
    - `GET /api/teachers/{id}/free-periods` (`teachers.py:259`)

**Security**

41. **JWT tokens live 7 days** (`ACCESS_TOKEN_EXPIRE_MINUTES=10080`,
    `config.py:10`) with no refresh, no revocation list. Compromised token
    = a week of access.
42. **CORS `allow_methods=["*"]` + `allow_headers=["*"]` + `allow_credentials=True`**
    (`main.py:20-23`). Narrow to the methods you use.
43. **Unbounded CSV upload size.** `schedule.py:114` and `teachers.py:94`
    `await file.read()` the entire file into memory. Add size cap.
44. **`create_substitution` takes IDs as raw query params** without existence
    check. `substitutions.py:85-89, 262-268`. Move to Pydantic body; validate
    FKs before commit.
45. **`bcrypt==3.2.2` + `passlib 1.7.4` are EOL/pinned old** (`requirements.txt:9,10`).
    Migrate to `argon2-cffi` or direct `bcrypt`.

**Code quality**

46. **TypeScript `WeekDay` type includes long-form aliases.**
    `frontend/lib/types.ts:7` — `type WeekDay = 'SUN'|...|'TUE'|...|'SUNDAY'
    |...|'TUESDAY'`. This is the *exact* shape that let the day bug happen.
    → Narrow to the 5 canonical codes; normalise at ingress only.
47. **`SchoolLevel` TS type is missing `PRESCHOOL`.** `types.ts:9`. Every
    PRESCHOOL teacher/lesson is currently untyped.
48. **`Substitution` TS interface out of sync.** `types.ts:39` still requires
    `dutyId` and has no `lessonId` or `sub_type`. Callers cast to
    `Record<string, unknown>` everywhere.
49. **Suggestion-scoring logic duplicated** between
    `substitutions.py:106-161` (duty) and `substitutions.py:300-400` (lesson).
    Extract a `SuggestionService`.
50. **400+ line router files bundle concerns.** `routers/substitutions.py`
    (400 lines), `routers/teachers.py` (276). Split by concern.
51. **620-line `frontend/app/(dashboard)/schedule/page.tsx`** — 10 sub-components
    in one file. Extract the import wizard to `components/schedule/ImportWizard/`.

### 💡 Nice-to-have

52. Missing DB indexes: `Lesson(teacherId, day)`, `Substitution.absentTeacherId`,
    `Substitution.lessonId`, `AuditLog.createdAt`.
53. `DAYS` label array duplicated in `substitutions/page.tsx:12-18` and
    `constants.ts:3-9` — import from constants.
54. Dead `TIME_SLOTS` constant (`constants.ts:11-15`) — 15 wrong entries,
    zero importers. Delete.
55. `Substitution.notes` and `Duty.notes` are unbounded VARCHAR — add cap.
56. `AuditLog` has free-text `details`; no `entity_type`/`entity_id`.
    Filtering by entity requires SQL LIKE.
57. `frontend/lib/utils.ts:20` hardcodes `en-US` locale — school is Saudi.
58. `bcrypt==3.2.2` pin is a passlib compat hack; unpin after migrating off.
59. No `pool_timeout` on the SQLAlchemy engine (default 30s hang under load).
60. Return type hints missing on every router function
    (`rules/python/coding-style.md` requires them).
61. `_duty_qual` map (`substitutions.py:21`) and `DUTY_TYPE_CONFIG`
    (`constants.ts:17`) drift silently — single source of truth.
62. Login page displays credentials in the UI (`login/page.tsx:76`).
    Remove before production build.
63. `ALLOWED_ORIGINS` in `render.yaml:19` includes a stale unrelated
    Vercel URL (`frontend-netguard.vercel.app`).
64. `Teacher.subjects` / `Teacher.qualifications` are unbounded JSON arrays
    — cap on Pydantic schema.
65. `Duty.updated_at` and `TeacherAttendance.updated_at` need
    `server_default=func.now()`.
66. Zero backend test coverage before this commit; only `tests/test_days.py`
    exists now. Adopt pytest + coverage per your global rule.
67. Zero frontend test coverage. No Playwright, no Vitest, no Jest. Stand
    up Playwright per your global rule (`tdd-guide` / e2e-runner agents).
68. `_run_column_migrations` uses `text()` with static strings — safe
    today, but the pattern invites future interpolation. Move to Alembic.
69. `axios` inline `Record<string, unknown>` casts across every hook —
    consider Zod-parsing at the API boundary.
70. Row-level `try/except Exception` in CSV import (`schedule.py:147`,
    `teachers.py:155`) swallows programmer errors. Narrow or log.
71. Prisma `DutyType` enum is out of date vs seed writes. Fixed by
    Critical #9 (delete Prisma).
72. Every mutating route ends with `db.commit()` inline; no unit-of-work.
    Consider a `services/` layer with rollback on error.
73. Git identity currently defaults to
    `mac@MACBOOKs-MacBook-Air.local` (see the last commit) — set global
    `user.name` / `user.email`.

---

## Prioritised fix list

Ordered by **blast radius reduction ÷ effort**. Items below are
independent — cherry-pick.

### 🔥 Do this session (minutes each — highest-impact, all near-zero-risk)

1. **[C3, C4]** Delete `/api/admin/debug-auth` and `/api/admin/debug-login`
   (`main.py:80-116`).
2. **[C2]** Delete the `force=True` branch of `/api/admin/seed` (`main.py:141-149`).
3. **[C1]** Remove the `SEED_KEY` default from `config.py:15` and delete
   the hardcoded value from `render.yaml:15`; rotate the key in Railway;
   refuse-to-boot check.
4. **[C12]** Fix the Settings 404 — either ship a placeholder
   `frontend/app/(dashboard)/settings/page.tsx` or remove from `Sidebar.tsx:27`.
5. **[C13]** Add a confirmation dialog before duty delete (`duties/page.tsx:88`).
6. **[C15]** Fix the dashboard lesson-sub crash — branch on `sub.sub_type`
   in `SubRequestPanel` (`dashboard/page.tsx:39-41`).
7. **[C10]** Remove or implement `_sync_teacher_profiles_from_lessons`
   (`main.py:41`).

### 🛠 This week (hours each)

8. **[C9]** Delete `frontend/prisma/` entirely; strip `@prisma/*`,
   `prisma`, `ts-node` from `package.json`; drop `prisma generate` from
   build/postinstall.
9. **[C8]** Fix the seed to write canonical day codes (`main.py:184`).
10. **[C6, C7]** Force password reset on first admin/teacher login;
    remove `Teacher@123` default from `schemas/teacher.py:16`; generate
    random passwords in bulk import (`teachers.py:134`); remove creds from
    README and login page.
11. **[C5]** Add `Depends(require_admin)` on every mutation and every
    admin-only read (all routers).
12. **[C16]** Add a shared `<QueryError>` component and wire `isError`
    into all 6 pages that lack it.
13. **[C11]** Replace `except Exception: pass` in startup with
    `logging.exception()` + fail-the-container.
14. **[C17]** Enable Railway Postgres backups; add a daily
    `pg_dump | gzip | rclone` cron; document restore in `README.md`.
15. **[C14]** Rewrite CSV download to use a blob + `URL.createObjectURL`
    (`reports/page.tsx:22`).
16. **[C18]** Delete the two orphan Postgres services after confirming
    they hold nothing needed.
17. **[C20]** Add `slowapi` rate limiting to `/auth/*` and `/admin/*`.
18. **[C19]** Migrate `python-jose` → `PyJWT >= 2.9`.
19. **[I34, I35]** Add `POST /api/attendance/teachers/bulk` and
    `POST /api/alerts/resolve-all`; wire from the two pages.
20. **[I37]** Fix `duties/new` conflict detection to check time overlap,
    not just non-empty day-grid.
21. **[I27]** Add PRESCHOOL to the teachers allow-list
    (`teachers.py:150`).

### 📅 Next 2 weeks (deeper changes)

22. Adopt Alembic properly; move the six `ALTER TABLE`s from
    `_run_column_migrations` into versioned revisions.
23. Consolidate `Absence` + `TeacherAttendance` into one table
    (I28); write a migration.
24. Add `/health` DB check and a real DB retry loop.
25. Update TypeScript types: narrow `WeekDay`, add `PRESCHOOL` to
    `SchoolLevel`, sync `Substitution` interface (I46-48).
26. Extract a `SuggestionService` for the duplicated ranking logic
    (I49).
27. Add teacher edit/delete UI (I36).
28. Add missing DB indexes (N52).
29. Split `schedule/page.tsx` and the two 400-line routers by concern.

### 🎁 Ongoing

30. Set up backend pytest + coverage gate (target 80% per your global
    rule). One test file exists today (`tests/test_days.py`).
31. Set up Playwright for the critical user flows: login, mark absent,
    request cover, assign substitute.

---

## Notes on methodology

- All findings gathered via read-only investigation forks — no code was
  modified during the audit.
- Live DB verified via read-only queries against Railway
  (`SELECT DISTINCT day FROM "Lesson"`; column-existence check;
  Adreen Khalil Haddad's Tuesday schedule).
- Bug-fix commit `27822f6` landed before this audit; several findings
  above (16, 46-48) are consequences of that commit that need
  follow-up.

## Appendix: how the DB-wipe fix stacks

Doing items 1–3 above (delete debug endpoints; delete force branch;
rotate SEED_KEY) removes **both wipe vectors** in under 20 minutes.
Item 8 (delete Prisma) removes the second vector. After those four
steps, the "wiped again" risk drops to accident-only (misuse of Railway
CLI/console), which items 14 (backups) and 22 (Alembic) then mitigate.
