"""Shared Anthropic Claude API client."""

import anthropic

from api.config import config


def get_claude_client(api_key_override: str | None = None) -> anthropic.Anthropic:
    """Return a configured Anthropic client.

    Raises RuntimeError if the API key is not set.
    """
    api_key = api_key_override or config.ANTHROPIC_API_KEY
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add your Anthropic API key to the .env file."
        )
    return anthropic.Anthropic(api_key=api_key)
