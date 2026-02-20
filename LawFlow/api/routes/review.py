"""Flash card / spaced repetition review routes."""

from flask import Blueprint, jsonify, request

from api.errors import ValidationError, NotFoundError
from api.services.spaced_repetition import (
    get_due_cards,
    get_card_stats,
    review_card,
    get_all_cards,
    delete_card,
    generate_cards_for_subject,
    generate_cards_for_chunk,
)

bp = Blueprint("review", __name__, url_prefix="/api/review")


@bp.route("/due", methods=["GET"])
def due_cards():
    """Get cards due for review, optionally filtered by subject."""
    subject = request.args.get("subject")
    limit = request.args.get("limit", 20, type=int)
    cards = get_due_cards(subject=subject, limit=limit)
    return jsonify(cards)


@bp.route("/stats", methods=["GET"])
def card_stats():
    """Get review statistics."""
    subject = request.args.get("subject")
    stats = get_card_stats(subject=subject)
    return jsonify(stats)


@bp.route("/cards", methods=["GET"])
def list_cards():
    """List all cards, optionally filtered by subject/topic."""
    subject = request.args.get("subject")
    topic = request.args.get("topic")
    cards = get_all_cards(subject=subject, topic=topic)
    return jsonify(cards)


@bp.route("/complete", methods=["POST"])
def complete_review():
    """Submit a card review with quality rating.

    Body: { "card_id": "...", "quality": 0-5 }
    Quality scale:
      0 = Complete blackout
      1 = Wrong but recognized answer
      2 = Wrong but close
      3 = Correct with difficulty
      4 = Correct with hesitation
      5 = Perfect instant recall
    """
    data = request.get_json(force=True)
    card_id = data.get("card_id")
    quality = data.get("quality")

    if not card_id:
        raise ValidationError("card_id is required")
    if quality is None or not isinstance(quality, int) or quality < 0 or quality > 5:
        raise ValidationError("quality must be an integer 0-5")

    try:
        updated = review_card(card_id, quality)
    except ValueError as e:
        raise NotFoundError(str(e))

    return jsonify(updated)


@bp.route("/generate/subject/<subject>", methods=["POST"])
def generate_subject_cards(subject: str):
    """Generate flashcards for the weakest topics in a subject.

    Uses Claude to analyze knowledge chunks and create cards.
    """
    max_chunks = request.args.get("max_chunks", 5, type=int)

    try:
        cards = generate_cards_for_subject(subject, max_chunks=max_chunks)
    except RuntimeError as e:
        raise ValidationError(str(e))

    return jsonify({
        "generated": len(cards),
        "cards": cards,
    })


@bp.route("/generate/chunk/<chunk_id>", methods=["POST"])
def generate_chunk_cards(chunk_id: str):
    """Generate flashcards from a specific knowledge chunk."""
    try:
        cards = generate_cards_for_chunk(chunk_id)
    except (ValueError, RuntimeError) as e:
        raise ValidationError(str(e))

    return jsonify({
        "generated": len(cards),
        "cards": cards,
    })


@bp.route("/cards/<card_id>", methods=["DELETE"])
def remove_card(card_id: str):
    """Delete a specific card."""
    if not delete_card(card_id):
        raise NotFoundError(f"Card {card_id} not found")
    return jsonify({"deleted": True})
