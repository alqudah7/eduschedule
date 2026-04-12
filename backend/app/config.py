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
