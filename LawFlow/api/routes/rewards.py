"""Rewards system routes — points summary, ledger, achievements, past test upload."""

import os
import uuid
import threading

from flask import Blueprint, request, jsonify

from api.config import config
from api.errors import ValidationError
from api.middleware.auth import get_current_user, get_current_user_id, login_required
from api.services import rewards_engine
from api.services.database import get_db
from api.models.document import Document
from api.services.tier_limits import check_tier_limit

bp = Blueprint("rewards", __name__, url_prefix="/api/rewards")

ALLOWED_EXTENSIONS = {"pdf", "pptx", "docx"}


@bp.before_request
@login_required
def require_auth():
    return None


@bp.route("/summary", methods=["GET"])
def summary():
    """Current balance, level, streak, title, and recent transactions."""
    return jsonify(rewards_engine.get_summary(user_id=get_current_user_id()))


@bp.route("/ledger", methods=["GET"])
def ledger():
    """Paginated point transaction history."""
    user_id = get_current_user_id()
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    activity_type = request.args.get("type")
    return jsonify(rewards_engine.get_ledger(limit, offset, activity_type, user_id=user_id))


@bp.route("/achievements", methods=["GET"])
def achievements():
    """All achievements with locked/unlocked state and progress."""
    return jsonify(rewards_engine.get_achievements(user_id=get_current_user_id()))


@bp.route("/past-test", methods=["POST"])
def upload_past_test():
    """Upload a graded past exam for analysis and points.

    This is the high-value action (150+ pts) that drives the data flywheel.
    Accepts graded exam papers, processes them, analyzes patterns, and
    awards points.
    """
    user_id = get_current_user_id()
    if "file" not in request.files:
        raise ValidationError("No file provided")

    file = request.files["file"]
    if not file.filename or not _allowed_file(file.filename):
        raise ValidationError(f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    subject = request.form.get("subject")
    if not subject:
        raise ValidationError("Subject is required for past test uploads")

    # Check file size
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise ValidationError(f"File too large. Max: {config.MAX_UPLOAD_MB}MB")

    # Save file
    ext = file.filename.rsplit(".", 1)[1].lower()
    doc_id = str(uuid.uuid4())
    filename = f"{doc_id}.{ext}"
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(config.UPLOAD_DIR, filename)
    file.save(file_path)

    # Create document record tagged as past_test
    with get_db() as db:
        check_tier_limit(db, get_current_user(), "document_uploads_total")
        doc = Document(
            id=doc_id,
            user_id=user_id,
            filename=file.filename,
            file_type=ext,
            file_path=file_path,
            file_size_bytes=size,
            subject=subject,
            doc_type="past_test",
            processing_status="pending",
        )
        db.add(doc)

    # Process and analyze in background
    thread = threading.Thread(target=_process_past_test, args=(doc_id, subject, user_id))
    thread.daemon = True
    thread.start()

    return jsonify({
        "id": doc_id,
        "status": "pending",
        "filename": file.filename,
        "message": "Processing your graded exam. Points will be awarded when analysis completes.",
    }), 201


def _process_past_test(doc_id: str, subject: str, user_id: str):
    """Background: process document, analyze exam patterns, award points."""
    from api.services.document_processor import extract_document, chunk_sections
    from api.services.knowledge_builder import tag_chunks_batch
    from api.models.document import KnowledgeChunk

    analysis_succeeded = False

    try:
        with get_db() as db:
            doc = db.query(Document).filter_by(id=doc_id, user_id=user_id).first()
            if not doc:
                return
            doc.processing_status = "processing"
            file_path = doc.file_path

        # Extract and chunk
        sections = extract_document(file_path)
        chunks = chunk_sections(sections)
        chunk_dicts = [{"content": c.content, "heading": c.heading} for c in chunks]
        tagged = tag_chunks_batch(chunk_dicts)

        # Save chunks
        with get_db() as db:
            for i, t in enumerate(tagged):
                db.add(KnowledgeChunk(
                    user_id=user_id,
                    document_id=doc_id,
                    content=t["content"],
                    summary=t.get("summary"),
                    chunk_index=i,
                    subject=t.get("subject", subject),
                    topic=t.get("topic"),
                    subtopic=t.get("subtopic"),
                    difficulty=t.get("difficulty", 50),
                    content_type=t.get("content_type", "concept"),
                    case_name=t.get("case_name"),
                    key_terms=t.get("key_terms", "[]"),
                ))
            doc = db.query(Document).filter_by(id=doc_id, user_id=user_id).first()
            if doc:
                doc.processing_status = "completed"
                doc.total_chunks = len(tagged)

        # Try exam analysis for blueprint generation
        try:
            from api.services.exam_analyzer import analyze_exam
            analyze_exam(doc_id, user_id=user_id)
            analysis_succeeded = True
        except Exception:
            pass  # Analysis is a bonus, not required

        # Award points: 150 base + 50 if analysis succeeded
        base = 150
        bonus_amount = 50 if analysis_succeeded else 0
        rewards_engine.award_points(
            activity_type="past_test_upload",
            activity_id=doc_id,
            description=f"Uploaded graded past test ({subject})",
            base_amount=base + bonus_amount,
            metadata={"subject": subject, "analysis_succeeded": analysis_succeeded},
            user_id=user_id,
        )

    except Exception as e:
        with get_db() as db:
            doc = db.query(Document).filter_by(id=doc_id, user_id=user_id).first()
            if doc:
                doc.processing_status = "error"
                doc.error_message = str(e)


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
