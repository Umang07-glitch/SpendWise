import os
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://spendwise:spendwise@localhost:5432/spendwise"
    cookie_secure: bool = False
    allowed_origins: str = Field(default_factory=lambda: os.getenv("RENDER_EXTERNAL_URL", "http://localhost:3000").rstrip("/"))
    session_days: int = 7
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        # Managed PostgreSQL providers supply URLs without a SQLAlchemy driver.
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix):]
        return value


settings = Settings()
