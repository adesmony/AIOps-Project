from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        hide_input_in_errors=True,
    )

    environment: str = Field(default="Production", validation_alias="ENVIRONMENT")
    port: int = Field(default=8000, ge=1, le=65535, validation_alias="PORT")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    cors_origins: str = Field(default="http://localhost:5173", validation_alias="CORS_ORIGINS")

    database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")
    azure_postgres_host: str | None = Field(default=None, validation_alias="AZURE_POSTGRES_HOST")
    azure_postgres_database: str | None = Field(
        default=None, validation_alias="AZURE_POSTGRES_DATABASE"
    )
    azure_postgres_user: str | None = Field(default=None, validation_alias="AZURE_POSTGRES_USER")
    database_timeout_seconds: float = Field(
        default=5.0, gt=0, le=30, validation_alias="DATABASE_TIMEOUT_SECONDS"
    )

    jwt_secret: SecretStr | None = Field(default=None, validation_alias="JWT_SECRET")
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = Field(
        default="HS256", validation_alias="JWT_ALGORITHM"
    )
    jwt_issuer: str = Field(default="incident-api", validation_alias="JWT_ISSUER")
    jwt_audience: str = Field(default="incident-web", validation_alias="JWT_AUDIENCE")
    jwt_expiry_minutes: int = Field(
        default=30, ge=5, le=1440, validation_alias="JWT_EXPIRY_MINUTES"
    )
    session_cookie_name: str = Field(
        default="incident_session", validation_alias="SESSION_COOKIE_NAME"
    )

    azure_openai_endpoint: str | None = Field(
        default=None, validation_alias="AZURE_OPENAI_ENDPOINT"
    )
    ai_provider: Literal["auto", "local", "openai"] = Field(
        default="auto", validation_alias="AI_PROVIDER"
    )
    gpt_model_api_key: SecretStr | None = Field(default=None, validation_alias="GPT_MODEL_API_KEY")
    gpt_model: str = Field(default="gpt-4.1-mini", validation_alias="GPT_MODEL")
    retrieval_mode: Literal["knowledge", "legacy"] = Field(
        default="knowledge", validation_alias="RETRIEVAL_MODE"
    )
    retrieval_min_score: float = Field(
        default=0.01, ge=0.001, le=1, validation_alias="RETRIEVAL_MIN_SCORE"
    )
    azure_openai_deployment: str | None = Field(
        default=None, validation_alias="AZURE_OPENAI_DEPLOYMENT"
    )
    azure_openai_embedding_deployment: str | None = Field(
        default=None, validation_alias="AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
    )
    azure_openai_api_version: str = Field(
        default="2024-10-21", validation_alias="AZURE_OPENAI_API_VERSION"
    )
    ai_timeout_seconds: float = Field(
        default=20.0, gt=0, le=60, validation_alias="AI_TIMEOUT_SECONDS"
    )
    ai_max_retries: int = Field(default=2, ge=0, le=4, validation_alias="AI_MAX_RETRIES")
    max_evidence_items: int = Field(default=12, ge=1, le=25, validation_alias="MAX_EVIDENCE_ITEMS")
    max_evidence_chars: int = Field(
        default=12000, ge=1000, le=30000, validation_alias="MAX_EVIDENCE_CHARS"
    )
    max_lookback_days: int = Field(default=7, ge=1, le=30, validation_alias="MAX_LOOKBACK_DAYS")
    default_lookback_minutes: int = Field(
        default=30, ge=1, le=1440, validation_alias="DEFAULT_LOOKBACK_MINUTES"
    )

    applicationinsights_connection_string: str | None = Field(
        default=None, validation_alias="APPLICATIONINSIGHTS_CONNECTION_STRING"
    )

    @property
    def is_development(self) -> bool:
        return self.environment == "Development"

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def uses_openai(self) -> bool:
        return self.ai_provider == "openai" or (
            self.ai_provider == "auto" and self.is_development and bool(self.gpt_model_api_key)
        )

    @model_validator(mode="after")
    def validate_selected_providers(self) -> "Settings":
        if self.ai_provider == "openai" and (
            self.gpt_model_api_key is None or not self.gpt_model_api_key.get_secret_value().strip()
        ):
            raise ValueError("GPT_MODEL_API_KEY is required when AI_PROVIDER=openai")
        if self.jwt_secret is None or len(self.jwt_secret.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 characters")
        if self.is_development:
            if not self.database_url:
                raise ValueError("DATABASE_URL is required when ENVIRONMENT=Development")
            return self

        required = {
            "AZURE_POSTGRES_HOST": self.azure_postgres_host,
            "AZURE_POSTGRES_DATABASE": self.azure_postgres_database,
            "AZURE_POSTGRES_USER": self.azure_postgres_user,
            "AZURE_OPENAI_ENDPOINT": self.azure_openai_endpoint,
            "AZURE_OPENAI_DEPLOYMENT": self.azure_openai_deployment,
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": self.azure_openai_embedding_deployment,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"Missing required production settings: {', '.join(missing)}")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
