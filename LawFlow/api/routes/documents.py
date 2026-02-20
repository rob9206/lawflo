"""Document upload and management routes."""

import os
import uuid
import threading

from flask import Blueprint, request, jsonify

from api.config import config
from api.errors import ValidationError, NotFoundError
from api.services.database import get_db
from api.models.document import Document, KnowledgeChunk
from api.services.document_processor import extract_document, chunk_sections
from api.services.knowledge_builder import tag_chunks_batch

bp = Blueprint("documents", __name__, url_prefix="/api/documents")

ALLOWED_EXTENSIONS = {"pdf", "pptx", "docx"}


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route("/upload", methods=["POST"])
def upload_document():
    """Upload a document for processing."""
    if "file" not in request.files:
        raise ValidationError("No file provided")

    file = request.files["file"]
    if not file.filename or not _allowed_file(file.filename):
        raise ValidationError(f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

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

    # Create document record
    subject = request.form.get("subject")
    doc_type = request.form.get("doc_type")

    with get_db() as db:
        doc = Document(
            id=doc_id,
            filename=file.filename,
            file_type=ext,
            file_path=file_path,
            file_size_bytes=size,
            subject=subject,
            doc_type=doc_type,
            processing_status="pending",
        )
        db.add(doc)

    # Process in background thread
    thread = threading.Thread(target=_process_document, args=(doc_id,))
    thread.daemon = True
    thread.start()

    return jsonify({"id": doc_id, "status": "pending", "filename": file.filename}), 201


def _process_document(doc_id: str):
    """Background processing: extract text, chunk, tag with Claude."""
    try:
        with get_db() as db:
            doc = db.query(Document).filter_by(id=doc_id).first()
            if not doc:
                return
            doc.processing_status = "processing"
            file_path = doc.file_path
            subject = doc.subject

        # Extract text
        sections = extract_document(file_path)
        chunks = chunk_sections(sections)

        # Prepare for tagging
        chunk_dicts = [{"content": c.content, "heading": c.heading} for c in chunks]

        # Tag with Claude (this is the expensive step)
        tagged = tag_chunks_batch(chunk_dicts)

        # Save to database
        with get_db() as db:
            for i, t in enumerate(tagged):
                kc = KnowledgeChunk(
                    document_id=doc_id,
                    content=t["content"],
                    summary=t.get("summary"),
                    chunk_index=i,
                    subject=t.get("subject", subject or "other"),
                    topic=t.get("topic"),
                    subtopic=t.get("subtopic"),
                    difficulty=t.get("difficulty", 50),
                    content_type=t.get("content_type", "concept"),
                    case_name=t.get("case_name"),
                    key_terms=t.get("key_terms", "[]"),
                )
                db.add(kc)

            doc = db.query(Document).filter_by(id=doc_id).first()
            if doc:
                doc.processing_status = "completed"
                doc.total_chunks = len(tagged)

    except Exception as e:
        with get_db() as db:
            doc = db.query(Document).filter_by(id=doc_id).first()
            if doc:
                doc.processing_status = "error"
                doc.error_message = str(e)


@bp.route("", methods=["GET"])
def list_documents():
    """List all documents."""
    with get_db() as db:
        query = db.query(Document).order_by(Document.created_at.desc())

        subject = request.args.get("subject")
        if subject:
            query = query.filter_by(subject=subject)

        status = request.args.get("status")
        if status:
            query = query.filter_by(processing_status=status)

        docs = query.all()
        return jsonify([d.to_dict() for d in docs])


@bp.route("/<doc_id>", methods=["GET"])
def get_document(doc_id: str):
    """Get document details."""
    with get_db() as db:
        doc = db.query(Document).filter_by(id=doc_id).first()
        if not doc:
            raise NotFoundError("Document not found")
        data = doc.to_dict()
        data["chunks"] = [c.to_dict() for c in doc.chunks]
        return jsonify(data)


@bp.route("/<doc_id>", methods=["DELETE"])
def delete_document(doc_id: str):
    """Delete a document and its chunks."""
    with get_db() as db:
        doc = db.query(Document).filter_by(id=doc_id).first()
        if not doc:
            raise NotFoundError("Document not found")

        # Delete file
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)

        db.delete(doc)
        return jsonify({"deleted": True})
