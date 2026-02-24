"""Spaced repetition service — SM-2 algorithm, card generation via Claude."""

import json
import logging
from datetime import datetime, timezone, timedelta

import anthropic

from api.config import config
from api.services.claude_client import get_claude_client
from api.services.database import get_db
from api.models.review import SpacedRepetitionCard
from api.models.document import KnowledgeChunk
from api.models.student import TopicMastery

logger = logging.getLogger(__name__)

# ── SM-2 Algorithm ──────────────────────────────────────────────────────────

def sm2_update(card: SpacedRepetitionCard, quality: int) -> SpacedRepetitionCard:
    """Apply SM-2 algorithm to update card scheduling.

    Quality scale (0-5):
      0 — Complete blackout, no recall at all
      1 — Wrong answer, but recognized the correct one
      2 — Wrong answer, but it felt close
      3 — Correct answer with serious difficulty
      4 — Correct answer with some hesitation
      5 — Perfect recall, instant

    Returns the updated card (mutated in place).
    """
    quality = max(0, min(5, quality))

    # Update ease factor (minimum 1.3)
    ef = card.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    card.ease_factor = max(1.3, ef)

    if quality < 3:
        # Failed — reset repetitions, review again soon
        card.repetitions = 0
        card.interval_days = 1
    else:
        if card.repetitions == 0:
            card.interval_days = 1
        elif card.repetitions == 1:
            card.interval_days = 3
        else:
            card.interval_days = round(card.interval_days * card.ease_factor)
        card.repetitions += 1

    now = datetime.now(timezone.utc)
    card.last_reviewed = now
    card.next_review = now + timedelta(days=card.interval_days)

    return card


# ── Card Generation via Claude ──────────────────────────────────────────────

CARD_GENERATION_PROMPT = """You are a law school flashcard generator. Given the following legal content, create study flashcards.

RULES:
- Each card should test ONE specific concept, rule, holding, or element
- Front: A clear, specific question a law professor might ask
- Back: A concise but complete answer with the rule/holding/reasoning
- Card types: "concept" (definitions/principles), "rule" (legal rules/tests), "case_holding" (case holdings), "element_list" (multi-element tests/factors)
- For element_list cards, format the back as a numbered list
- Generate 3-5 high-quality cards per chunk
- Focus on what would appear on a law school exam

Respond with ONLY a JSON array (no markdown fencing):
[
  {
    "front": "What is the test for ...",
    "back": "The test requires ...",
    "card_type": "rule"
  }
]

CONTENT:
"""


def _get_client() -> anthropic.Anthropic:
    return get_claude_client()


def generate_cards_for_chunk(chunk_id: str, user_id: str | None = None) -> list[dict]:
    """Generate flashcards from a single knowledge chunk using Claude."""
    with get_db() as db:
        chunk = db.query(KnowledgeChunk).filter_by(id=chunk_id, user_id=user_id).first()
        if not chunk:
            raise ValueError(f"Chunk {chunk_id} not found")

        subject = chunk.subject or "other"
        topic = chunk.topic
        content = chunk.content

    client = _get_client()
    truncated = content[:4000] if len(content) > 4000 else content

    try:
        response = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": CARD_GENERATION_PROMPT + truncated}],
        )
        text = response.content[0].text.strip()

        # Strip markdown fencing if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        cards_data = json.loads(text)
    except (json.JSONDecodeError, anthropic.APIError) as e:
        logger.warning(f"Failed to generate cards for chunk {chunk_id}: {e}")
        return []

    # Save cards to database
    now = datetime.now(timezone.utc)
    created_cards = []

    with get_db() as db:
        for card_data in cards_data:
            card = SpacedRepetitionCard(
                user_id=user_id,
                chunk_id=chunk_id,
                subject=subject,
                topic=topic,
                front=card_data["front"],
                back=card_data["back"],
                card_type=card_data.get("card_type", "concept"),
                next_review=now,  # Available immediately
            )
            db.add(card)
            db.flush()
            created_cards.append(card.to_dict())

    return created_cards


def generate_cards_for_subject(
    subject: str,
    max_chunks: int = 10,
    user_id: str | None = None,
) -> list[dict]:
    """Generate flashcards for the weakest topics in a subject."""
    with get_db() as db:
        # Find weakest topics
        weak_topics = (
            db.query(TopicMastery)
            .filter_by(user_id=user_id, subject=subject)
            .order_by(TopicMastery.mastery_score)
            .limit(5)
            .all()
        )
        weak_topic_names = [t.topic for t in weak_topics]

        # Find chunks for those topics that don't already have cards
        existing_chunk_ids = {
            row[0]
            for row in db.query(SpacedRepetitionCard.chunk_id)
            .filter(
                SpacedRepetitionCard.user_id == user_id,
                SpacedRepetitionCard.subject == subject,
            )
            .all()
            if row[0]
        }

        chunks_query = db.query(KnowledgeChunk).filter(
            KnowledgeChunk.user_id == user_id,
            KnowledgeChunk.subject == subject
        )
        
        # Only filter by weak topics if they exist AND match chunks
        if weak_topic_names:
            chunks_query = chunks_query.filter(
                KnowledgeChunk.topic.in_(weak_topic_names)
            )
            chunks = chunks_query.limit(max_chunks * 2).all()
            
            # If no chunks found with weak topics, fall back to any chunks for this subject
            if not chunks:
                logger.info(f"No chunks found for weak topics {weak_topic_names}, using all subject chunks")
                chunks_query = db.query(KnowledgeChunk).filter(
                    KnowledgeChunk.user_id == user_id,
                    KnowledgeChunk.subject == subject
                )
                chunks = chunks_query.limit(max_chunks * 2).all()
        else:
            # No weak topics tracked yet, use any chunks for this subject
            chunks = chunks_query.limit(max_chunks * 2).all()

        # Filter out chunks that already have cards
        new_chunks = [c for c in chunks if c.id not in existing_chunk_ids][:max_chunks]

    all_cards = []
    for chunk in new_chunks:
        try:
            cards = generate_cards_for_chunk(chunk.id, user_id=user_id)
            all_cards.extend(cards)
        except Exception as e:
            logger.warning(f"Failed to generate cards for chunk {chunk.id}: {e}")
            continue

    return all_cards


# ── Card Review Operations ──────────────────────────────────────────────────

def get_due_cards(
    subject: str | None = None,
    limit: int = 20,
    user_id: str | None = None,
) -> list[dict]:
    """Get cards that are due for review."""
    now = datetime.now(timezone.utc)

    with get_db() as db:
        query = db.query(SpacedRepetitionCard).filter(
            SpacedRepetitionCard.user_id == user_id,
            SpacedRepetitionCard.next_review <= now
        )
        if subject:
            query = query.filter(SpacedRepetitionCard.subject == subject)

        # Order: overdue first (oldest next_review), then by ease (hardest first)
        cards = (
            query
            .order_by(SpacedRepetitionCard.next_review)
            .limit(limit)
            .all()
        )
        return [c.to_dict() for c in cards]


def get_card_stats(subject: str | None = None, user_id: str | None = None) -> dict:
    """Get review statistics."""
    now = datetime.now(timezone.utc)

    with get_db() as db:
        base = db.query(SpacedRepetitionCard).filter(SpacedRepetitionCard.user_id == user_id)
        if subject:
            base = base.filter(SpacedRepetitionCard.subject == subject)

        total = base.count()
        due = base.filter(SpacedRepetitionCard.next_review <= now).count()
        new = base.filter(SpacedRepetitionCard.repetitions == 0).count()
        learning = base.filter(
            SpacedRepetitionCard.repetitions > 0,
            SpacedRepetitionCard.interval_days <= 7,
        ).count()
        mature = base.filter(SpacedRepetitionCard.interval_days > 7).count()

        return {
            "total": total,
            "due": due,
            "new": new,
            "learning": learning,
            "mature": mature,
        }


def review_card(card_id: str, quality: int, user_id: str | None = None) -> dict:
    """Review a card with a quality rating (0-5). Returns updated card."""
    with get_db() as db:
        card = db.query(SpacedRepetitionCard).filter_by(id=card_id, user_id=user_id).first()
        if not card:
            raise ValueError(f"Card {card_id} not found")

        sm2_update(card, quality)
        db.flush()
        return card.to_dict()


def get_all_cards(
    subject: str | None = None,
    topic: str | None = None,
    user_id: str | None = None,
) -> list[dict]:
    """Get all cards, optionally filtered."""
    with get_db() as db:
        query = db.query(SpacedRepetitionCard).filter(SpacedRepetitionCard.user_id == user_id)
        if subject:
            query = query.filter(SpacedRepetitionCard.subject == subject)
        if topic:
            query = query.filter(SpacedRepetitionCard.topic == topic)

        cards = query.order_by(SpacedRepetitionCard.created_at.desc()).all()
        return [c.to_dict() for c in cards]


def delete_card(card_id: str, user_id: str | None = None) -> bool:
    """Delete a specific card."""
    with get_db() as db:
        card = db.query(SpacedRepetitionCard).filter_by(id=card_id, user_id=user_id).first()
        if not card:
            return False
        db.delete(card)
        return True
