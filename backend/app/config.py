from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080
    ALLOWED_ORIGINS: str = '["http://localhost:3000","http://localhost:3002"]'
    RESEND_API_KEY: str = ""
    FRONTEND_URL: str = "http://localhost:3000"
    PYTHON_VERSION: str = "3.11.0"
    # ENV gates dev-only endpoints (e.g. /api/admin/seed). Default "development"
    # is safe because production is expected to set ENV=production explicitly.
    ENV: str = "development"

    # Phase 3 — subdomain-based tenant resolution.
    #
    # TENANT_PARENT_DOMAIN is the wildcard root under which tenant
    # subdomains live (e.g. ".eduschedule.app" → alhekma.eduschedule.app,
    # sunrise.eduschedule.app). Leading dot is required so we can tell
    # apex from a tenant. Value is a placeholder until wildcard DNS is
    # provisioned; the resolver falls back to DEFAULT_TENANT_SLUG below.
    TENANT_PARENT_DOMAIN: str = ".eduschedule.app"
    # DEFAULT_TENANT_SLUG bridges the period between "prod runs on a
    # single fixed alias" and "wildcard DNS is live". While set, requests
    # with no resolvable tenant subdomain fall through to this school.
    # Once the wildcard cert is deployed, set this to "" so any request
    # to an unknown subdomain returns 404 with UNKNOWN_TENANT.
    DEFAULT_TENANT_SLUG: str = "alhekma"
    # ALLOW_TENANT_HEADER — dev and test only. Enables the X-Tenant-Slug
    # header for out-of-browser tools (curl, pytest). MUST be false in
    # production; the app would otherwise accept a tenant identity from
    # arbitrary client input, which was the pre-Phase-2 vulnerability.
    ALLOW_TENANT_HEADER: bool = False

    @property
    def database_url_fixed(self) -> str:
        """Render provides postgres:// but SQLAlchemy needs postgresql://"""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url

    @property
    def allowed_origins_list(self) -> List[str]:
        try:
            return json.loads(self.ALLOWED_ORIGINS)
        except Exception:
            return [self.ALLOWED_ORIGINS]

    class Config:
        env_file = ".env"


settings = Settings()
