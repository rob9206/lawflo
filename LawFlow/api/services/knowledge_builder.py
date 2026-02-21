"""Build structured knowledge chunks from extracted document text using Claude."""

import json
import logging

import anthropic

from api.config import config
from api.services.claude_client import get_claude_client

logger = logging.getLogger(__name__)

TAGGING_PROMPT = """You are a law school content classifier. Given a text excerpt from a law school document, extract structured metadata.

Respond with ONLY a JSON object (no markdown fencing, no explanation):
{
  "subject": "<one of: con_law, contracts, torts, crim_law, civ_pro, property, evidence, crim_pro, admin_law, prof_responsibility, or 'other'>",
  "topic": "<specific topic within the subject, e.g. 'consideration', 'equal_protection', 'negligence'>",
  "subtopic": "<even more specific subtopic if applicable, else null>",
  "content_type": "<one of: rule, case, concept, procedure, hypo, analysis, definition, example>",
  "case_name": "<if this discusses a specific case, its name, else null>",
  "difficulty": <0-100 integer, where 0=basic and 100=advanced>,
  "key_terms": ["list", "of", "key", "legal", "terms"],
  "summary": "<1-2 sentence summary of the content>"
}

TEXT EXCERPT:
"""


def _get_client() -> anthropic.Anthropic:
    return get_claude_client()


def tag_chunk(content: str) -> dict:
    """Send a text chunk to Claude for subject/topic tagging.

    Returns a dict with: subject, topic, subtopic, content_type,
    case_name, difficulty, key_terms, summary.
    """
    client = _get_client()

    truncated = content[:3000] if len(content) > 3000 else content

    try:
        response = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": TAGGING_PROMPT + truncated}],
        )
        text = response.content[0].text.strip()

        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        return json.loads(text)
    except anthropic.AuthenticationError as e:
        logger.error(f"Anthropic authentication failed: {e}")
        raise RuntimeError(
            "Anthropic API key is invalid. Check ANTHROPIC_API_KEY in your .env file."
        ) from e
    except (json.JSONDecodeError, anthropic.APIError) as e:
        logger.warning(f"Failed to tag chunk: {e}")
        return {
            "subject": "other",
            "topic": None,
            "subtopic": None,
            "content_type": "concept",
            "case_name": None,
            "difficulty": 50,
            "key_terms": [],
            "summary": content[:200],
        }


def tag_chunks_batch(chunks: list[dict]) -> list[dict]:
    """Tag multiple chunks. Each dict must have a 'content' key.

    Returns the same dicts with tagging metadata merged in.
    """
    results = []
    for chunk in chunks:
        tags = tag_chunk(chunk["content"])
        merged = {**chunk, **tags}
        merged["key_terms"] = json.dumps(tags.get("key_terms", []))
        results.append(merged)
    return results
