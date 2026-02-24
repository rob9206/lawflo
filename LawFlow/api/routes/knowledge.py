"""Knowledge base search and browsing routes."""

from flask import Blueprint, jsonify, request

from api.middleware.auth import get_current_user_id, login_required
from api.services.database import get_db
from api.models.document import KnowledgeChunk, Document

bp = Blueprint("knowledge", __name__, url_prefix="/api/knowledge")


@bp.before_request
@login_required
def require_auth():
    return None


@bp.route("/search", methods=["GET"])
def search():
    """Search knowledge chunks."""
    q = request.args.get("q", "")
    subject = request.args.get("subject")
    topic = request.args.get("topic")
    content_type = request.args.get("content_type")
    limit = request.args.get("limit", 20, type=int)

    user_id = get_current_user_id()
    with get_db() as db:
        query = db.query(KnowledgeChunk).filter(KnowledgeChunk.user_id == user_id)

        if subject:
            query = query.filter(KnowledgeChunk.subject == subject)
        if topic:
            query = query.filter(KnowledgeChunk.topic == topic)
        if content_type:
            query = query.filter(KnowledgeChunk.content_type == content_type)
        if q:
            query = query.filter(KnowledgeChunk.content.ilike(f"%{q}%"))

        chunks = query.limit(limit).all()
        return jsonify([c.to_dict() for c in chunks])


@bp.route("/subjects", methods=["GET"])
def list_subjects():
    """List all subjects with chunk counts."""
    user_id = get_current_user_id()
    with get_db() as db:
        from sqlalchemy import func
        results = (
            db.query(KnowledgeChunk.subject, func.count(KnowledgeChunk.id))
            .filter(KnowledgeChunk.user_id == user_id)
            .group_by(KnowledgeChunk.subject)
            .all()
        )
        return jsonify([{"subject": r[0], "chunk_count": r[1]} for r in results])


@bp.route("/topics/<subject>", methods=["GET"])
def list_topics(subject: str):
    """List all topics for a subject with chunk counts."""
    user_id = get_current_user_id()
    with get_db() as db:
        from sqlalchemy import func
        results = (
            db.query(KnowledgeChunk.topic, func.count(KnowledgeChunk.id))
            .filter(
                KnowledgeChunk.user_id == user_id,
                KnowledgeChunk.subject == subject,
            )
            .group_by(KnowledgeChunk.topic)
            .all()
        )
        return jsonify([{"topic": r[0], "chunk_count": r[1]} for r in results])
