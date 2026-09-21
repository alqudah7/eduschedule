// Rendered by frontend/middleware.ts when the requested subdomain
// does not map to a known tenant. Kept dependency-free and
// server-rendered so it responds even if the API is down.

export const dynamic = "force-static";

export default function TenantNotFoundPage() {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "2rem",
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        background: "#f9fafb",
        color: "#111827",
      }}
    >
      <div style={{ maxWidth: "480px", textAlign: "center" }}>
        <h1 style={{ fontSize: "1.75rem", marginBottom: "0.75rem" }}>
          School not found
        </h1>
        <p style={{ marginBottom: "1rem", lineHeight: 1.5 }}>
          This EduSchedule subdomain isn&#39;t associated with an active
          school.
        </p>
        <p style={{ fontSize: "0.9rem", color: "#4b5563" }}>
          Check the address bar, or contact your school administrator
          for the correct link.
        </p>
      </div>
    </main>
  );
}
