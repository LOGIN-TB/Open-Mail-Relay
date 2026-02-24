from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Admin Panel
    SECRET_KEY: str = "change-me-in-production"
    ADMIN_DEFAULT_PASSWORD: str = "admin"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # Hostnames
    MAIL_HOSTNAME: str = "mail-relay.example.com"
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


# Singleton – override SECRET_KEY & MAIL_HOSTNAME from env without prefix too
class _Settings(Settings):
    model_config = {"env_prefix": "", "env_file": ".env", "extra": "ignore"}


settings = Settings()
# Also pick up MAIL_HOSTNAME without prefix
import os

if val := os.getenv("MAIL_HOSTNAME"):
    settings.MAIL_HOSTNAME = val
if val := os.getenv("ADMIN_HOSTNAME"):
    settings.ADMIN_HOSTNAME = val
if val := os.getenv("ADMIN_SECRET_KEY"):
    settings.SECRET_KEY = val
if val := os.getenv("ADMIN_DEFAULT_PASSWORD"):
    settings.ADMIN_DEFAULT_PASSWORD = val
