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

// Parent domain the wildcard is hosted under. Read from an env var
// so preview deploys on *.vercel.app do not blow up — they fall
// through to the default tenant instead.
const PARENT_DOMAIN = (process.env.NEXT_PUBLIC_TENANT_PARENT_DOMAIN || "")
  .toLowerCase()
  .replace(/^\.+/, "");

const DEFAULT_TENANT = (process.env.NEXT_PUBLIC_DEFAULT_TENANT_SLUG || "").toLowerCase();

// Paths that don't need a tenant identity — the "no such school"
// page itself, static assets, health probes.
const OPEN_PATHS = [
  "/tenant-not-found",
  "/_next",
  "/favicon.ico",
  "/robots.txt",
];

function extractSlug(hostHeader: string): string | null {
  // Strip port and lowercase.
  const host = hostHeader.split(":", 1)[0].toLowerCase();

  // Localhost / IP / preview deploy — no wildcard in play. Use the
  // default slug so `next dev` keeps working out of the box.
  if (!PARENT_DOMAIN || !host.endsWith("." + PARENT_DOMAIN)) {
    return DEFAULT_TENANT || null;
  }

  const label = host.slice(0, host.length - PARENT_DOMAIN.length - 1);
  if (!label || label.includes(".")) return null;   // apex or nested
  if (RESERVED_SUBDOMAINS.has(label)) return null;
  if (!SLUG_RE.test(label)) return null;
  return label;
}

export function middleware(req: NextRequest) {
  // Static paths and the not-found page itself skip the check.
  const { pathname } = req.nextUrl;
  if (OPEN_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/"))) {
    return NextResponse.next();
  }

  const slug = extractSlug(req.headers.get("host") || "");
  if (slug === null) {
    // Bogus subdomain. Rewrite (not redirect) so the URL bar keeps
    // the user's chosen subdomain — they can see what they typed.
    const url = req.nextUrl.clone();
    url.pathname = "/tenant-not-found";
    return NextResponse.rewrite(url);
  }

  // Pass the resolved slug to server components + client code via a
  // response header and a non-httpOnly cookie. Both are advisory —
  // the API resolves tenant identity independently from Origin/Referer,
  // so a client that forges this cookie only breaks their own UX.
  const res = NextResponse.next();
  res.headers.set("x-tenant-slug", slug);
  res.cookies.set("tenant_slug", slug, {
    path: "/",
    sameSite: "lax",
    httpOnly: false,
  });
  return res;
}

export const config = {
  matcher: [
    // Everything except Next.js internals and image optimisation.
    "/((?!_next/static|_next/image|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
};
