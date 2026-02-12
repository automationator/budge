from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "Budge"
    debug: bool = False
    env: str = "development"  # "development", "production", "e2e"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    extra_cors_origins: list[str] = []  # Additional origins (e.g., Tailscale hostname)
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # Logging
    log_level: str = "INFO"

    # JWT
    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        import os

        env = os.getenv("ENV", "development")
        if env == "production":
            if v == "CHANGE_ME_IN_PRODUCTION":
                raise ValueError(
                    "JWT_SECRET_KEY must be set in production. "
                    "Generate one with: openssl rand -base64 32"
                )
            if len(v) < 32:
                raise ValueError(
                    "JWT_SECRET_KEY must be at least 32 characters in production"
                )
        return v

    # Version & Updates
    app_version: str = "dev"
    github_repo: str = "automationator/budge"

    # Database
    postgres_user: str = "budge"
    postgres_password: str = "budge"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "budge"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        """Sync database URL for Alembic migrations."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
