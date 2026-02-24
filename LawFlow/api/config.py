"""LawFlow application configuration."""

import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

_override_env_path = os.getenv("LAWFLOW_ENV_PATH")
if _override_env_path:
    _env_path = Path(_override_env_path).expanduser().resolve()
else:
    _env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path, override=True)


@dataclass
class Config:
    # Flask
    SECRET_KEY: str = field(default_factory=lambda: os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me"))
    DEBUG: bool = field(default_factory=lambda: os.getenv("FLASK_DEBUG", "true").lower() == "true")
    HOST: str = field(default_factory=lambda: os.getenv("FLASK_HOST", "127.0.0.1"))
    PORT: int = field(default_factory=lambda: int(os.getenv("FLASK_PORT", "5002")))

    # Anthropic
    ANTHROPIC_API_KEY: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    CLAUDE_MODEL: str = field(default_factory=lambda: os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"))

    # Auth / JWT
    JWT_SECRET_KEY: str = field(default_factory=lambda: os.getenv("JWT_SECRET_KEY", os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")))
    JWT_ACCESS_EXPIRES_MINUTES: int = field(default_factory=lambda: int(os.getenv("JWT_ACCESS_EXPIRES_MINUTES", "60")))
    JWT_REFRESH_EXPIRES_DAYS: int = field(default_factory=lambda: int(os.getenv("JWT_REFRESH_EXPIRES_DAYS", "30")))

    # Billing
    STRIPE_SECRET_KEY: str = field(default_factory=lambda: os.getenv("STRIPE_SECRET_KEY", ""))
    STRIPE_PUBLISHABLE_KEY: str = field(default_factory=lambda: os.getenv("STRIPE_PUBLISHABLE_KEY", ""))
    STRIPE_WEBHOOK_SECRET: str = field(default_factory=lambda: os.getenv("STRIPE_WEBHOOK_SECRET", ""))
    STRIPE_PRO_PRICE_ID: str = field(default_factory=lambda: os.getenv("STRIPE_PRO_PRICE_ID", ""))
    APP_BASE_URL: str = field(default_factory=lambda: os.getenv("APP_BASE_URL", "http://localhost:5173"))

    # Storage
    UPLOAD_DIR: str = field(default_factory=lambda: os.getenv("UPLOAD_DIR", "data/uploads"))
    PROCESSED_DIR: str = field(default_factory=lambda: os.getenv("PROCESSED_DIR", "data/processed"))
    DATABASE_URL: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///data/lawflow.db"))
    MAX_UPLOAD_MB: int = field(default_factory=lambda: int(os.getenv("MAX_UPLOAD_MB", "100")))


config = Config()
