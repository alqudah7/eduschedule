#!/usr/bin/env bash
# Dump the EduSchedule Postgres database to a gzipped .sql file.
#
# Usage:
#   DATABASE_URL=postgresql://... ./ops/backup.sh
#
# Environment:
#   DATABASE_URL  Required. Postgres connection string.
#   BACKUP_DIR    Optional. Defaults to ./backups.
#
# Exit codes:
#   0  success
#   1  DATABASE_URL missing
#   2  pg_dump not on PATH
#   3  pg_dump failed
set -euo pipefail

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: DATABASE_URL not set" >&2
  exit 1
fi

if ! command -v pg_dump >/dev/null 2>&1; then
  echo "ERROR: pg_dump not on PATH. Install postgresql-client." >&2
  exit 2
fi

TS=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP_DIR="${BACKUP_DIR:-./backups}"
OUT="${BACKUP_DIR}/eduschedule-${TS}.sql.gz"
mkdir -p "${BACKUP_DIR}"

# --no-owner + --no-acl make the dump portable to a fresh DB with a
# different superuser (Railway's provisioning changes usernames).
if ! pg_dump "$DATABASE_URL" --no-owner --no-acl | gzip -9 > "$OUT"; then
  echo "ERROR: pg_dump failed" >&2
  rm -f "$OUT"
  exit 3
fi

SIZE=$(du -h "$OUT" | cut -f1)
echo "Wrote ${OUT} (${SIZE})"
