"""Flash card / spaced repetition review routes."""

from flask import Blueprint, jsonify, request

from api.errors import ValidationError, NotFoundError
from api.middleware.auth import get_current_user, get_current_user_id, login_required
from api.services.database import get_db
from api.services.spaced_repetition import (
    get_due_cards,
    get_card_stats,
    review_card,
    get_all_cards,
    delete_card,
    generate_cards_for_subject,
    generate_cards_for_chunk,
)
from api.services.tier_limits import check_tier_limit

bp = Blueprint("review", __name__, url_prefix="/api/review")


@bp.before_request
@login_required
def require_auth():
    return None


@bp.route("/due", methods=["GET"])
def due_cards():
    """Get cards due for review, optionally filtered by subject."""
    user_id = get_current_user_id()
    subject = request.args.get("subject")
    limit = request.args.get("limit", 20, type=int)
    cards = get_due_cards(subject=subject, limit=limit, user_id=user_id)
    return jsonify(cards)


@bp.route("/stats", methods=["GET"])
def card_stats():
    """Get review statistics."""
    user_id = get_current_user_id()
    subject = request.args.get("subject")
    stats = get_card_stats(subject=subject, user_id=user_id)
    return jsonify(stats)


@bp.route("/cards", methods=["GET"])
def list_cards():
    """List all cards, optionally filtered by subject/topic."""
    user_id = get_current_user_id()
    subject = request.args.get("subject")
    topic = request.args.get("topic")
    cards = get_all_cards(subject=subject, topic=topic, user_id=user_id)
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
    user_id = get_current_user_id()
    data = request.get_json(force=True)
    card_id = data.get("card_id")
    quality = data.get("quality")

    if not card_id:
        raise ValidationError("card_id is required")
    if quality is None or not isinstance(quality, int) or quality < 0 or quality > 5:
        raise ValidationError("quality must be an integer 0-5")

    try:
        updated = review_card(card_id, quality, user_id=user_id)
    except ValueError as e:
        raise NotFoundError(str(e))

    return jsonify(updated)


@bp.route("/generate/subject/<subject>", methods=["POST"])
def generate_subject_cards(subject: str):
    """Generate flashcards for the weakest topics in a subject.

    Uses Claude to analyze knowledge chunks and create cards.
    """
    user_id = get_current_user_id()
    max_chunks = request.args.get("max_chunks", 5, type=int)

    try:
        with get_db() as db:
            check_tier_limit(db, get_current_user(), "flashcard_generations_daily")
        cards = generate_cards_for_subject(subject, max_chunks=max_chunks, user_id=user_id)
    except RuntimeError as e:
        raise ValidationError(str(e))

    return jsonify({
        "generated": len(cards),
        "cards": cards,
    })


@bp.route("/generate/chunk/<chunk_id>", methods=["POST"])
def generate_chunk_cards(chunk_id: str):
    """Generate flashcards from a specific knowledge chunk."""
    user_id = get_current_user_id()
    try:
        with get_db() as db:
            check_tier_limit(db, get_current_user(), "flashcard_generations_daily")
        cards = generate_cards_for_chunk(chunk_id, user_id=user_id)
    except (ValueError, RuntimeError) as e:
        raise ValidationError(str(e))

    return jsonify({
        "generated": len(cards),
        "cards": cards,
    })


@bp.route("/complete-session", methods=["POST"])
def complete_flashcard_session():
    """Award points for a completed flashcard review session.

    Called by the frontend when the flashcard session completion screen renders.
    Body: { "cards_reviewed": int, "avg_quality": float }
    """
    user_id = get_current_user_id()
    data = request.get_json(force=True)
    cards = data.get("cards_reviewed", 0)
    avg_quality = data.get("avg_quality", 3.0)

    if cards <= 0:
        return jsonify({"points_awarded": 0, "message": "No cards reviewed"})

    # 3 pts/card + 1 extra/card if avg quality >= 4 (Good/Easy)
    base = cards * 3 + (cards if avg_quality >= 4 else 0)

    try:
        from api.services.rewards_engine import award_points
        result = award_points(
            "flashcard_session", None,
            f"Reviewed {cards} flashcards",
            base_amount=base,
            metadata={"cards": cards, "avg_quality": round(avg_quality, 2)},
            user_id=user_id,
        )
        return jsonify(result)
    except Exception:
        return jsonify({"points_awarded": 0, "message": "Error awarding points"})


@bp.route("/cards/<card_id>", methods=["DELETE"])
def remove_card(card_id: str):
    """Delete a specific card."""
    user_id = get_current_user_id()
    if not delete_card(card_id, user_id=user_id):
        raise NotFoundError(f"Card {card_id} not found")
    return jsonify({"deleted": True})
