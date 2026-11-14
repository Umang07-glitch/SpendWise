from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://spendwise:spendwise@localhost:5432/spendwise"
    cookie_secure: bool = False
    allowed_origins: str = "http://localhost:3000"
    session_days: int = 7
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
