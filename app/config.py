"""Configuration management for Bullet."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server settings
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=5032)
    log_level: str = Field(default="INFO")

    # Routes configuration
    routes_config: str = Field(default="routes.yaml")

    # Resend email channel (optional)
    resend_api_key: str = Field(default="")
    resend_from_email: str = Field(default="")
    resend_api_url: str = Field(default="https://api.resend.com/emails")

    @property
    def routes_config_path(self) -> Path:
        return Path(self.routes_config)


@lru_cache
def get_settings() -> Settings:
    return Settings()

