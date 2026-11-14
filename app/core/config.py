from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.security import validate_jwt_secret


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str
    mock: bool = False
    allowed_origins: list[str] = Field(default_factory=list)
    llm_provider: str = "anthropic"
    llm_api_key: SecretStr | None = None
    llm_model: str = "claude-3-5-sonnet-latest"
    llm_base_url: str | None = None
    llm_embedding_model: str | None = None
    llm_timeout_seconds: float = Field(default=30.0, gt=0)
    llm_max_retries: int = Field(default=1, ge=0)
    jwt_secret: SecretStr

    @field_validator("allowed_origins")
    @classmethod
    def validate_allowed_origins(cls, origins: list[str]) -> list[str]:
        if "*" in origins:
            raise ValueError("ALLOWED_ORIGINS must list explicit origins; '*' is not allowed")
        if any(not origin.strip() for origin in origins):
            raise ValueError("ALLOWED_ORIGINS cannot contain empty values")
        return origins

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret_value(cls, secret: SecretStr) -> SecretStr:
        validate_jwt_secret(secret.get_secret_value())
        return secret


@lru_cache
def get_settings() -> Settings:
    return Settings()
