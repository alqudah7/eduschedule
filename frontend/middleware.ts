// Phase 3 subdomain awareness.
//
// The web app runs under a wildcard (e.g. alhekma.eduschedule.app,
// sunrise.eduschedule.app). Middleware runs on every request and:
//
//   1. Extracts the tenant slug from the Host header.
//   2. Rewrites unknown-tenant requests to the /tenant-not-found page
//      so the visitor sees a helpful message instead of a broken app.
//   3. Sets a NEXT_PUBLIC-visible cookie so client-side code can read
//      the current tenant slug without re-parsing the URL. The API
//      does its OWN authoritative resolution — this cookie is a UX
//      convenience, never a source of truth.
//
// Rules the runtime is designed around:
//   - No env var is authoritative. The Host header is.
//   - Middleware never talks to the backend. Tenant validity is
//     enforced by the API at request time; this file only handles
//     the "obviously bogus subdomain" cases (bad chars, reserved
//     names, apex-with-no-www).
//   - This is Node/Edge runtime code (Next.js 16 middleware).

import { NextRequest, NextResponse } from "next/server";

// Kept in sync with backend/app/services/tenant_resolver.py — any
// subdomain in this set is treated as "not a tenant".
const RESERVED_SUBDOMAINS = new Set([
  "www", "api", "admin", "app", "docs", "status",
]);

// Slug rules match the backend regex ^[a-z0-9](?:[a-z0-9-]{0,30}[a-z0-9])?$
const SLUG_RE = /^[a-z0-9](?:[a-z0-9-]{0,30}[a-z0-9])?$/;

// Parent domain the wildcard is hosted under. When the env var is
// unset (current production state, pre-wildcard-DNS), middleware
// treats every host as "wildcard inactive" and does no rewriting —
// tenant identity is decided server-side by the backend's
// DEFAULT_TENANT_SLUG. This is critical: unset MUST NOT be a
// synonym for "invalid subdomain" or every request 404s on hosts
// like eduschedulealhekma.vercel.app.
const PARENT_DOMAIN = (process.env.NEXT_PUBLIC_TENANT_PARENT_DOMAIN || "")
  .toLowerCase()
  .replace(/^\.+/, "");

// Paths that don't need a tenant identity — the "no such school"
// page itself, static assets, health probes.
const OPEN_PATHS = [
  "/tenant-not-found",
  "/_next",
  "/favicon.ico",
  "/robots.txt",
];

// Three-state result: we deliberately distinguish "wildcard doesn't
// apply here" (pass through) from "wildcard applies but the label is
// bogus" (rewrite to not-found).
type SubdomainResult =
  | { kind: "wildcard-inactive" }         // host is not under PARENT_DOMAIN; do nothing
  | { kind: "valid"; slug: string }       // recognisable tenant subdomain
  | { kind: "invalid" };                  // under wildcard but slug is reserved/malformed

function extractSubdomain(hostHeader: string): SubdomainResult {
  const host = hostHeader.split(":", 1)[0].toLowerCase();

  // PARENT_DOMAIN unset OR host is on a different domain entirely
  // (vercel.app, localhost, custom preview host) → the wildcard is
  // not in effect for this request. Do NOT rewrite. Let the backend's
  // DEFAULT_TENANT_SLUG (or a real tenant Origin) settle it.
  if (!PARENT_DOMAIN || !host.endsWith("." + PARENT_DOMAIN)) {
    return { kind: "wildcard-inactive" };
  }

  const label = host.slice(0, host.length - PARENT_DOMAIN.length - 1);
  if (!label || label.includes(".")) return { kind: "invalid" };   // apex or nested
  if (RESERVED_SUBDOMAINS.has(label)) return { kind: "invalid" };
  if (!SLUG_RE.test(label)) return { kind: "invalid" };
  return { kind: "valid", slug: label };
}

export function middleware(req: NextRequest) {
  // Static paths and the not-found page itself skip the check.
  const { pathname } = req.nextUrl;
  if (OPEN_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/"))) {
    return NextResponse.next();
  }

  const result = extractSubdomain(req.headers.get("host") || "");

  if (result.kind === "invalid") {
    // Under the wildcard, but the slug is reserved/malformed. Rewrite
    // (not redirect) so the URL bar keeps what the user typed.
    const url = req.nextUrl.clone();
    url.pathname = "/tenant-not-found";
    return NextResponse.rewrite(url);
  }

  const res = NextResponse.next();
  if (result.kind === "valid") {
    // Pass the resolved slug forward as advisory metadata. The API
    // resolves tenant identity independently from Origin/Referer, so
    // a forged cookie only breaks its own UX.
    res.headers.set("x-tenant-slug", result.slug);
    res.cookies.set("tenant_slug", result.slug, {
      path: "/",
      sameSite: "lax",
      httpOnly: false,
    });
  }
  return res;
}

export const config = {
  matcher: [
    // Everything except Next.js internals and image optimisation.
    "/((?!_next/static|_next/image|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
};
