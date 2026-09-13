from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    PROJECT_NAME: str = "FastAPI E-Commerce API"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database Configuration (PostgreSQL with asyncpg)
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/ecommerce"
    DB_POOL_MIN_SIZE: int = 5
    DB_POOL_MAX_SIZE: int = 20
    DB_POOL_MAX_INACTIVE_CONNECTION_LIFETIME: float = 300.0
    DB_POOL_TIMEOUT: float = 30.0

    # Security & JWT Authentication
    JWT_SECRET_KEY: str = "super-secret-key-change-in-production-min-32-chars-long!"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Google Authentication
    GOOGLE_CLIENT_ID: str = ""

    # Cloudflare R2 Public Media URL (Bucket / Custom Domain)
    R2_PUBLIC_URL: str = ""

    # CORS Configuration
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []


settings = Settings()
