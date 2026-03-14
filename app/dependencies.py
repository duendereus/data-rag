"""Dependency injection factories for FastAPI."""

from functools import lru_cache

from app.config import Settings


@lru_cache
def get_settings() -> Settings:
    """Return the singleton Settings instance."""
    return Settings()
