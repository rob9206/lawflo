"""LawFlow application configuration."""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


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

    # Storage
    UPLOAD_DIR: str = field(default_factory=lambda: os.getenv("UPLOAD_DIR", "data/uploads"))
    PROCESSED_DIR: str = field(default_factory=lambda: os.getenv("PROCESSED_DIR", "data/processed"))
    DATABASE_URL: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///data/lawflow.db"))
    MAX_UPLOAD_MB: int = field(default_factory=lambda: int(os.getenv("MAX_UPLOAD_MB", "100")))


config = Config()
