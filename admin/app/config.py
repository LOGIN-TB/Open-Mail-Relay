from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Admin Panel
    SECRET_KEY: str = "change-me-in-production"
    ADMIN_DEFAULT_PASSWORD: str = "admin"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # Hostname (nur Admin-Interface; Mail-Hostname wird in postfix/main.cf verwaltet)
    ADMIN_HOSTNAME: str = "admin.example.com"

    # Paths
    POSTFIX_CONFIG_PATH: Path = Path("/etc/postfix-config")
    DATABASE_PATH: Path = Path("/app/data/admin.db")

    # Docker
    MAIL_RELAY_CONTAINER: str = "open-mail-relay"

    # Stats
    LOG_RETENTION_DAYS: int = 30
    STATS_RETENTION_DAYS: int = 365

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.DATABASE_PATH}"

    model_config = {"env_prefix": "ADMIN_", "env_file": ".env", "extra": "ignore"}


# Singleton – override Settings from env without prefix
settings = Settings()

import os

if val := os.getenv("ADMIN_HOSTNAME"):
    settings.ADMIN_HOSTNAME = val
if val := os.getenv("ADMIN_SECRET_KEY"):
    settings.SECRET_KEY = val
if val := os.getenv("ADMIN_DEFAULT_PASSWORD"):
    settings.ADMIN_DEFAULT_PASSWORD = val
