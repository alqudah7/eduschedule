#!/usr/bin/env bash
# post-deploy-check.sh — smoke test the URL users actually visit.
#
# Rationale: our Batch 4 verification hit synthetic Origin headers
# against the API but never fetched the real Vercel URL. The wildcard-
# subdomain middleware then took the whole site down for ~5 hours
# because "PARENT_DOMAIN unset" was treated as "invalid subdomain".
# This script exists so that class of miss can never repeat silently.
#
# Every deploy MUST end with this returning exit 0. Wire it into a
# GitHub Action / Railway hook / Vercel deploy webhook later; today
# it is called by hand.
#
# Usage:
#   ops/post-deploy-check.sh                         # default URLs
#   FRONTEND_URL=... BACKEND_URL=... ops/post-deploy-check.sh
#
# Exit codes:
#   0  everything green
#   1  a check failed — the deploy is broken, do not close the change

set -euo pipefail

FRONTEND_URL="${FRONTEND_URL:-https://eduschedulealhekma.vercel.app}"
BACKEND_URL="${BACKEND_URL:-https://eduschedule-api-production.up.railway.app}"

TMP=$(mktemp -t post-deploy-XXXXXX)
trap 'rm -f "$TMP"' EXIT

fail() {
    echo "  ✗ FAIL: $1" >&2
    exit 1
}

pass() {
    echo "  ✓ $1"
}

echo "== Post-deploy check =="
echo "  frontend: $FRONTEND_URL"
echo "  backend:  $BACKEND_URL"
echo

# ── Frontend ─────────────────────────────────────────────────────────────
echo "-- Frontend --"

CODE=$(curl -s -o "$TMP" -w "%{http_code}" "$FRONTEND_URL/login")
[ "$CODE" = "200" ] || fail "GET /login returned HTTP $CODE (expected 200)"
pass "GET /login → 200"

# The tenant-not-found page ships a distinctive string. If middleware
# rewrites the login page to it, every real visitor gets this response
# — the exact outage we are guarding against.
if grep -qi "School not found" "$TMP"; then
    fail "response body contains 'School not found' — middleware is rewriting to /tenant-not-found. This is the Batch-4-class outage."
fi
pass "response body does NOT contain 'School not found'"

# Sanity that we actually rendered the login form. A blank 200 would
# be a different kind of broken.
if ! grep -qEi 'password|sign ?in|log ?in' "$TMP"; then
    fail "response body does not look like a login page (no password/sign-in text)"
fi
pass "response body looks like the login form"

# ── Backend ──────────────────────────────────────────────────────────────
echo
echo "-- Backend --"

CODE=$(curl -s -o "$TMP" -w "%{http_code}" "$BACKEND_URL/health")
[ "$CODE" = "200" ] || fail "GET /health returned HTTP $CODE"
grep -q '"status":"ok"' "$TMP" || fail "/health body is not {status:ok}"
pass "GET /health → 200 ok"

# Login endpoint MUST accept a request whose Origin matches the frontend
# URL (which is not under the wildcard). If enforce_tenant_matches_jwt
# ever regresses to 403-ing this class of Origin, the frontend cannot
# talk to the API at all.
CODE=$(curl -s -o "$TMP" -w "%{http_code}" -X POST "$BACKEND_URL/api/auth/login" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    -H "Origin: $FRONTEND_URL" \
    --data 'username=nonexistent-smoke-user@example.invalid&password=x')
# 401 is the CORRECT response (bad credentials); anything else is
# suspicious. Specifically we DO NOT want 403 (tenant mismatch) or
# 404 UNKNOWN_TENANT for a real frontend Origin.
if [ "$CODE" = "403" ] || [ "$CODE" = "404" ]; then
    body=$(cat "$TMP" | head -c 200)
    fail "POST /api/auth/login from real frontend Origin returned $CODE — backend is treating a legit Origin as an unknown tenant. Body: $body"
fi
[ "$CODE" = "401" ] || fail "POST /api/auth/login unexpected HTTP $CODE (expected 401)"
pass "POST /api/auth/login with Origin=$FRONTEND_URL → 401 (bad creds, tenant check skipped correctly)"

echo
echo "== ALL POST-DEPLOY CHECKS PASSED =="
