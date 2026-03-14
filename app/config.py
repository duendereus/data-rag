"""Application configuration via environment variables."""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All application settings, validated at startup."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM provider
    LLM_PROVIDER: str  # "anthropic" or "openai"
    LLM_MODEL: str
    LLM_MAX_TOKENS: int = 2048

    # API keys (conditional on provider)
    ANTHROPIC_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str | None = None

    # Database
    DUCKDB_PATH: str = "./data/datasets.db"

    # File uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # Query
    QUERY_RESULT_LIMIT: int = 1000

    # Logging
    LOG_LEVEL: str = "INFO"

    @model_validator(mode="after")
    def validate_api_keys(self) -> "Settings":
        """Ensure the correct API key is set for the chosen provider."""
        if self.LLM_PROVIDER == "anthropic" and not self.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")
        if self.LLM_PROVIDER == "openai" and not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        return self
