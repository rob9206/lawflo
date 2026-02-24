"""Document upload and management routes."""

import os
import uuid
import threading
from pathlib import Path

from flask import Blueprint, request, jsonify, send_file

from api.config import config
from api.errors import ValidationError, NotFoundError
from api.middleware.auth import get_current_user, get_current_user_id, login_required
from api.services.database import get_db
from api.models.document import Document, KnowledgeChunk
from api.services.document_processor import extract_document, chunk_sections
from api.services.knowledge_builder import tag_chunks_batch
from api.services.document_converter import convert_document
from api.services.tier_limits import check_tier_limit

bp = Blueprint("documents", __name__, url_prefix="/api/documents")

ALLOWED_EXTENSIONS = {"pdf", "pptx", "docx"}


@bp.before_request
@login_required
def require_auth():
    return None


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route("/upload", methods=["POST"])
def upload_document():
    """Upload a document for processing."""
    user_id = get_current_user_id()

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
        check_tier_limit(db, get_current_user(), "document_uploads_total")
        doc = Document(
            id=doc_id,
            user_id=user_id,
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
    thread = threading.Thread(target=_process_document, args=(doc_id, user_id))
    thread.daemon = True
    thread.start()

    return jsonify({"id": doc_id, "status": "pending", "filename": file.filename}), 201


def _process_document(doc_id: str, user_id: str):
    """Background processing: extract text, chunk, tag with Claude."""
    try:
        with get_db() as db:
            doc = db.query(Document).filter_by(id=doc_id, user_id=user_id).first()
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
                    user_id=user_id,
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

            doc = db.query(Document).filter_by(id=doc_id, user_id=user_id).first()
            if doc:
                doc.processing_status = "completed"
                doc.total_chunks = len(tagged)

    except Exception as e:
        with get_db() as db:
            doc = db.query(Document).filter_by(id=doc_id, user_id=user_id).first()
            if doc:
                doc.processing_status = "error"
                doc.error_message = str(e)


@bp.route("", methods=["GET"])
def list_documents():
    """List all documents."""
    user_id = get_current_user_id()
    with get_db() as db:
        query = (
            db.query(Document)
            .filter_by(user_id=user_id)
            .order_by(Document.created_at.desc())
        )

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
    user_id = get_current_user_id()
    with get_db() as db:
        doc = db.query(Document).filter_by(id=doc_id, user_id=user_id).first()
        if not doc:
            raise NotFoundError("Document not found")
        data = doc.to_dict()
        data["chunks"] = [c.to_dict() for c in doc.chunks]
        return jsonify(data)


@bp.route("/<doc_id>", methods=["DELETE"])
def delete_document(doc_id: str):
    """Delete a document and its chunks."""
    user_id = get_current_user_id()
    with get_db() as db:
        doc = db.query(Document).filter_by(id=doc_id, user_id=user_id).first()
        if not doc:
            raise NotFoundError("Document not found")

        # Delete file
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)

        db.delete(doc)
        return jsonify({"deleted": True})


@bp.route("/<doc_id>/convert", methods=["POST"])
def convert_doc(doc_id: str):
    """Convert a document to a different format.
    
    Request body:
    {
        "format": "pdf" | "png" | "txt" | "md"
    }
    
    Returns the converted file for download or info about generated files.
    """
    user_id = get_current_user_id()
    with get_db() as db:
        doc = db.query(Document).filter_by(id=doc_id, user_id=user_id).first()
        if not doc:
            raise NotFoundError("Document not found")
        
        if doc.file_type != "pptx":
            raise ValidationError("Only PPTX files can be converted currently")
    
    data = request.get_json() or {}
    output_format = data.get("format", "pdf")
    
    if output_format not in ["pdf", "png", "txt", "md"]:
        raise ValidationError(f"Invalid format. Allowed: pdf, png, txt, md")
    
    try:
        # Generate output path
        output_dir = os.path.join(config.UPLOAD_DIR, "converted")
        os.makedirs(output_dir, exist_ok=True)
        
        base_name = os.path.splitext(os.path.basename(doc.file_path))[0]
        
        if output_format == "png":
            output_path = os.path.join(output_dir, f"{base_name}_slides")
        else:
            output_path = os.path.join(output_dir, f"{base_name}.{output_format}")
        
        # Perform conversion
        result_path = convert_document(doc.file_path, output_format, output_path)
        
        # For image conversion, return list of files
        if output_format == "png":
            image_files = sorted([f for f in os.listdir(result_path) if f.endswith('.png')])
            return jsonify({
                "format": output_format,
                "message": f"Converted to {len(image_files)} images",
                "files": image_files,
                "download_url": f"/api/documents/{doc_id}/converted/{os.path.basename(result_path)}"
            })
        
        # For single file formats, offer download
        return jsonify({
            "format": output_format,
            "message": "Conversion successful",
            "download_url": f"/api/documents/{doc_id}/download/{os.path.basename(result_path)}"
        })
    
    except Exception as e:
        raise ValidationError(f"Conversion failed: {str(e)}")


@bp.route("/<doc_id>/download/<filename>", methods=["GET"])
def download_converted(doc_id: str, filename: str):
    """Download a converted file."""
    user_id = get_current_user_id()
    with get_db() as db:
        doc = db.query(Document).filter_by(id=doc_id, user_id=user_id).first()
        if not doc:
            raise NotFoundError("Document not found")
    
    converted_dir = os.path.join(config.UPLOAD_DIR, "converted")
    file_path = os.path.join(converted_dir, filename)
    
    if not os.path.exists(file_path):
        raise NotFoundError("Converted file not found")
    
    # Security check: ensure file is within converted directory
    if not Path(file_path).resolve().is_relative_to(Path(converted_dir).resolve()):
        raise ValidationError("Invalid file path")
    
    return send_file(file_path, as_attachment=True, download_name=filename)
