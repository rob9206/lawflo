"""Document and KnowledgeChunk models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from api.models.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("idx_doc_user", "user_id"),
    )

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # pdf, pptx, docx
    file_path = Column(String, nullable=False)
    file_size_bytes = Column(Integer)
    subject = Column(String)  # e.g. 'contracts', 'torts'
    doc_type = Column(String)  # casebook, slides, outline, exam, supplement
    processing_status = Column(String, default="pending")  # pending, processing, completed, error
    error_message = Column(Text)
    total_chunks = Column(Integer, default=0)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "filename": self.filename,
            "file_type": self.file_type,
            "file_size_bytes": self.file_size_bytes,
            "subject": self.subject,
            "doc_type": self.doc_type,
            "processing_status": self.processing_status,
            "error_message": self.error_message,
            "total_chunks": self.total_chunks,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        Index("idx_kc_user", "user_id"),
        Index("idx_kc_subject", "user_id", "subject"),
        Index("idx_kc_topic", "user_id", "subject", "topic"),
        Index("idx_kc_type", "content_type"),
        Index("idx_kc_document", "document_id"),
    )

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text)
    chunk_index = Column(Integer, nullable=False)
    subject = Column(String, nullable=False)
    topic = Column(String)
    subtopic = Column(String)
    difficulty = Column(Integer, default=50)  # 0-100
    content_type = Column(String, nullable=False)  # rule, case, concept, procedure, hypo, analysis
    case_name = Column(String)
    key_terms = Column(Text)  # JSON array
    cross_references = Column(Text)  # JSON array of chunk IDs
    created_at = Column(DateTime, default=_now)

    document = relationship("Document", back_populates="chunks")

    def to_dict(self) -> dict:
        import json
        return {
            "id": self.id,
            "document_id": self.document_id,
            "content": self.content,
            "summary": self.summary,
            "chunk_index": self.chunk_index,
            "subject": self.subject,
            "topic": self.topic,
            "subtopic": self.subtopic,
            "difficulty": self.difficulty,
            "content_type": self.content_type,
            "case_name": self.case_name,
            "key_terms": json.loads(self.key_terms) if self.key_terms else [],
            "cross_references": json.loads(self.cross_references) if self.cross_references else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
