"""Shared Anthropic client construction with robust key normalization."""

import json
import os
import time

import anthropic
from flask import has_request_context, request

from api.config import config

_QUOTE_CHARS = "\"'`“”‘’"
_DEBUG_LOG_PATH = r"c:\Dev\LawFlow\.claude\worktrees\charming-dewdney\.cursor\debug.log"


def _normalize_api_key(raw: str | None) -> str:
    """Normalize common copy/paste artifacts around API keys."""
    key = (raw or "").strip()
    if not key:
        return ""

    # Some shells/tools store keys as "Bearer <token>".
    if key.lower().startswith("bearer "):
        key = key[7:].strip()

    # Trim surrounding quote characters if present.
    while len(key) >= 2 and key[0] in _QUOTE_CHARS and key[-1] in _QUOTE_CHARS:
        key = key[1:-1].strip()

    return key


def _looks_like_anthropic_key(key: str) -> bool:
    return key.startswith("sk-ant-") and len(key) >= 40


def _debug_log(hypothesis_id: str, message: str, data: dict):
    # #region agent log
    try:
        os.makedirs(os.path.dirname(_DEBUG_LOG_PATH), exist_ok=True)
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "id": f"log_{int(time.time() * 1000)}_anthropic_client",
                        "timestamp": int(time.time() * 1000),
                        "runId": "pre-fix",
                        "hypothesisId": hypothesis_id,
                        "location": "api/services/anthropic_client.py:resolve_anthropic_api_key",
                        "message": message,
                        "data": data,
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion


def _request_header_api_key() -> str:
    """Read optional per-request key override from frontend."""
    if not has_request_context():
        return ""
    return _normalize_api_key(request.headers.get("X-Anthropic-Api-Key", ""))


def resolve_anthropic_api_key(override_key: str | None = None) -> str:
    """Resolve Anthropic API key from config/env with sanity checks."""
    explicit_key = _normalize_api_key(override_key)
    header_key = _request_header_api_key()
    config_key = _normalize_api_key(config.ANTHROPIC_API_KEY)
    env_key = _normalize_api_key(os.getenv("ANTHROPIC_API_KEY", ""))
    explicit_valid = _looks_like_anthropic_key(explicit_key)
    header_valid = _looks_like_anthropic_key(header_key)
    config_valid = _looks_like_anthropic_key(config_key)
    env_valid = _looks_like_anthropic_key(env_key)
    selected_source = ""

    if explicit_valid:
        selected_source = "explicit_override"
        selected_key = explicit_key
    elif header_valid:
        selected_source = "header"
        selected_key = header_key
    elif not config_key and not env_key:
        _debug_log(
            "H3",
            "No key candidates available",
            {
                "header_len": len(header_key),
                "config_len": len(config_key),
                "env_len": len(env_key),
            },
        )
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. "
            "Add your Anthropic API key to the .env file."
        )
    elif config_valid and not env_valid:
        selected_source = "config"
        selected_key = config_key
    elif env_valid and not config_valid:
        selected_source = "env"
        selected_key = env_key
    else:
        # Preserve existing precedence when both are similarly valid/invalid.
        selected_source = "config" if config_key else "env"
        selected_key = config_key or env_key

    _debug_log(
        "H3",
        "Resolved Anthropic key source",
        {
                "explicit_present": bool(explicit_key),
                "explicit_len": len(explicit_key),
                "explicit_valid": explicit_valid,
            "header_present": bool(header_key),
            "header_len": len(header_key),
            "header_valid": header_valid,
            "config_present": bool(config_key),
            "config_len": len(config_key),
            "config_valid": config_valid,
            "env_present": bool(env_key),
            "env_len": len(env_key),
            "env_valid": env_valid,
            "selected_source": selected_source,
            "selected_len": len(selected_key),
        },
    )
    return selected_key


def create_anthropic_client(override_key: str | None = None) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=resolve_anthropic_api_key(override_key))
