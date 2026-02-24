"""Core AI tutor engine — session management, prompt construction, Claude streaming."""

import json
import re
import logging
from datetime import datetime, timezone

import anthropic

from api.config import config
from api.services.claude_client import get_claude_client
from api.services.prompt_library import build_system_prompt, build_student_context, build_knowledge_context, build_exam_context, build_time_context
from api.services.database import get_db
from api.models.session import StudySession, SessionMessage
from api.models.student import SubjectMastery, TopicMastery
from api.models.document import KnowledgeChunk

logger = logging.getLogger(__name__)


def _clean_markdown(text: str) -> str:
    """Clean up common markdown formatting issues in AI-generated content.
    
    Fixes:
    - Concatenated words (adds spaces)
    - Unclosed markdown tags
    - Missing spaces after punctuation
    - Broken markdown syntax
    """
    if not text:
        return text

    # Remove performance metadata blocks before markdown processing.
    text = re.sub(r"<performance>[\s\S]*?</performance>", "", text).strip()
    
    # Fix concatenated words (words stuck together without spaces)
    # Pattern: lowercase letter followed by uppercase letter (e.g., "wordWord" -> "word Word")
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    
    # Fix missing spaces after punctuation (but preserve URLs and decimals)
    text = re.sub(r'([.!?])([A-Za-z])', r'\1 \2', text)
    text = re.sub(r'([,;:])([A-Za-z])', r'\1 \2', text)
    
    # Fix unclosed bold tags (ensure ** is always paired)
    # Count opening and closing ** tags
    bold_open = text.count('**') % 2
    if bold_open == 1:  # Odd number means unclosed tag
        # Find the last ** and check if it's opening or closing
        last_bold_pos = text.rfind('**')
        if last_bold_pos != -1:
            # If it's an opening tag, add closing at end
            text = text + '**'
    
    # Fix markdown headers that are missing spaces (e.g., "##Header" -> "## Header")
    text = re.sub(r'(#{1,6})([A-Za-z])', r'\1 \2', text)
    
    # Remove extra whitespace but preserve intentional blank lines
    lines = text.split('\n')
    cleaned_lines = []
    prev_empty = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if not prev_empty:  # Allow one blank line
                cleaned_lines.append('')
                prev_empty = True
        else:
            cleaned_lines.append(stripped)
            prev_empty = False
    
    return '\n'.join(cleaned_lines)


def _get_client(api_key_override: str | None = None) -> anthropic.Anthropic:
    return get_claude_client(api_key_override)


def create_session(
    mode: str,
    subject: str | None = None,
    topics: list[str] | None = None,
    available_minutes: int | None = None,
    session_type: str = "tutor",
    user_id: str | None = None,
) -> dict:
    """Create a new tutoring session."""
    with get_db() as db:
        session = StudySession(
            user_id=user_id,
            session_type=session_type,
            tutor_mode=mode,
            subject=subject,
            topics=json.dumps(topics or []),
            available_minutes=available_minutes,
        )
        db.add(session)
        db.flush()
        return session.to_dict()


def get_session(session_id: str, user_id: str | None = None) -> dict | None:
    """Get session with message history."""
    with get_db() as db:
        session = db.query(StudySession).filter_by(id=session_id, user_id=user_id).first()
        if not session:
            return None
        data = session.to_dict()
        messages = (
            db.query(SessionMessage)
            .filter_by(session_id=session_id, user_id=user_id)
            .order_by(SessionMessage.message_index)
            .all()
        )
        data["messages"] = [m.to_dict() for m in messages]
        return data


def _get_mastery_context(subject: str | None = None, user_id: str | None = None) -> str:
    """Build student mastery context for the system prompt."""
    with get_db() as db:
        query = db.query(SubjectMastery).filter_by(user_id=user_id)
        if subject:
            query = query.filter_by(subject=subject)
        subjects = query.all()

        mastery_data = []
        for s in subjects:
            topics = (
                db.query(TopicMastery)
                .filter_by(user_id=user_id, subject=s.subject)
                .order_by(TopicMastery.mastery_score)
                .all()
            )
            weak = [t.to_dict() for t in topics[:3]]
            strong = [t.to_dict() for t in topics[-3:]] if len(topics) > 3 else []
            mastery_data.append({
                **s.to_dict(),
                "weak_topics": weak,
                "strong_topics": strong,
            })

        return build_student_context(mastery_data)


def _get_knowledge_context(
    subject: str | None,
    topics: list[str] | None,
    query: str,
    user_id: str | None = None,
) -> str:
    """Retrieve relevant knowledge chunks for RAG context."""
    with get_db() as db:
        q = db.query(KnowledgeChunk).filter(KnowledgeChunk.user_id == user_id)
        if subject:
            q = q.filter(KnowledgeChunk.subject == subject)
        if topics:
            q = q.filter(KnowledgeChunk.topic.in_(topics))

        if query:
            keywords = query.lower().split()
            for kw in keywords[:5]:
                q = q.filter(KnowledgeChunk.content.ilike(f"%{kw}%"))

        chunks = q.limit(8).all()

        if not chunks:
            return ""

        chunk_dicts = []
        for c in chunks:
            doc = c.document
            chunk_dicts.append({
                "content": c.content,
                "filename": doc.filename if doc else "Unknown",
                "chunk_index": c.chunk_index,
                "summary": c.summary or "",
                "content_type": c.content_type or "",
                "case_name": c.case_name or "",
                "difficulty": c.difficulty,
            })

        return build_knowledge_context(chunk_dicts)


def _get_exam_context(subject: str, user_id: str | None = None) -> str:
    """Build exam intelligence context if past exams have been analyzed."""
    from api.models.exam_blueprint import ExamBlueprint
    with get_db() as db:
        blueprint = (
            db.query(ExamBlueprint)
            .filter_by(user_id=user_id, subject=subject)
            .order_by(ExamBlueprint.created_at.desc())
            .first()
        )
        if not blueprint:
            return ""
        return build_exam_context(blueprint.to_dict())


def send_message(
    session_id: str,
    user_content: str,
    api_key_override: str | None = None,
    user_id: str | None = None,
):
    """Send a user message and stream Claude's response.

    Yields text chunks for SSE streaming. Saves both messages to DB.
    """
    with get_db() as db:
        session = db.query(StudySession).filter_by(id=session_id, user_id=user_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Count existing messages
        msg_count = db.query(SessionMessage).filter_by(session_id=session_id, user_id=user_id).count()

        # Save user message
        user_msg = SessionMessage(
            user_id=user_id,
            session_id=session_id,
            role="user",
            content=user_content,
            message_index=msg_count,
        )
        db.add(user_msg)
        db.flush()

        # Build message history
        history_rows = (
            db.query(SessionMessage)
            .filter_by(session_id=session_id, user_id=user_id)
            .order_by(SessionMessage.message_index)
            .all()
        )
        messages = [{"role": m.role, "content": m.content} for m in history_rows if m.role in ("user", "assistant")]

    # Build system prompt
    mode = session.tutor_mode or "explain"
    subject = session.subject
    topics = json.loads(session.topics) if session.topics else None
    avail_min = session.available_minutes

    student_ctx = _get_mastery_context(subject, user_id=user_id)
    knowledge_ctx = _get_knowledge_context(subject, topics, user_content, user_id=user_id)
    exam_ctx = _get_exam_context(subject, user_id=user_id) if subject else ""
    time_ctx = build_time_context(avail_min)
    system_prompt = build_system_prompt(mode, student_ctx, knowledge_ctx, exam_ctx, time_ctx)

    # Stream from Claude
    client = _get_client(api_key_override)
    full_response = ""

    with client.messages.stream(
        model=config.CLAUDE_MODEL,
        max_tokens=2000,
        system=system_prompt,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            full_response += text
            yield text

    # Clean up markdown formatting before saving
    cleaned_response = _clean_markdown(full_response)
    
    # Save assistant message
    _save_assistant_message(session_id, cleaned_response, msg_count + 1, user_id=user_id)

    # Extract and apply performance signals
    _process_performance_signals(session_id, full_response, user_id=user_id)


def _save_assistant_message(
    session_id: str,
    content: str,
    index: int,
    user_id: str | None = None,
):
    """Save the assistant's response to the database."""
    # Strip performance tags from stored content for cleaner display
    clean_content = re.sub(r"<performance>.*?</performance>", "", content, flags=re.DOTALL).strip()
    # Additional markdown cleanup
    clean_content = _clean_markdown(clean_content)

    with get_db() as db:
        msg = SessionMessage(
            user_id=user_id,
            session_id=session_id,
            role="assistant",
            content=clean_content,
            message_index=index,
        )
        db.add(msg)

        # Update session message count
        session = db.query(StudySession).filter_by(id=session_id, user_id=user_id).first()
        if session:
            session.messages_count = index + 1


def _process_performance_signals(
    session_id: str,
    response: str,
    user_id: str | None = None,
):
    """Parse <performance> JSON from Claude's response and update mastery scores."""
    match = re.search(r"<performance>\s*(\{.*?\})\s*</performance>", response, re.DOTALL)
    if not match:
        return

    try:
        signals = json.loads(match.group(1))
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse performance signals for session {session_id}")
        return

    mastery_deltas = signals.get("mastery_delta", {})
    if not mastery_deltas:
        return

    with get_db() as db:
        session = db.query(StudySession).filter_by(id=session_id, user_id=user_id).first()
        subject = session.subject if session else None

        for topic_name, delta in mastery_deltas.items():
            if not subject:
                continue

            topic = db.query(TopicMastery).filter_by(
                user_id=user_id,
                subject=subject,
                topic=topic_name,
            ).first()
            if topic:
                new_score = max(0, min(100, topic.mastery_score + delta))
                topic.mastery_score = new_score
                topic.exposure_count += 1
                topic.last_studied_at = datetime.now(timezone.utc)

                if delta > 0:
                    topic.correct_count += 1
                elif delta < 0:
                    topic.incorrect_count += 1

        # Update subject-level mastery (average of topic scores)
        if subject:
            subj = db.query(SubjectMastery).filter_by(user_id=user_id, subject=subject).first()
            if subj:
                topics = db.query(TopicMastery).filter_by(user_id=user_id, subject=subject).all()
                if topics:
                    subj.mastery_score = sum(t.mastery_score for t in topics) / len(topics)
                subj.sessions_count += 1
                subj.last_studied_at = datetime.now(timezone.utc)


def end_session(session_id: str, user_id: str | None = None) -> dict | None:
    """End a session and return a summary."""
    with get_db() as db:
        session = db.query(StudySession).filter_by(id=session_id, user_id=user_id).first()
        if not session:
            return None

        now = datetime.now(timezone.utc)
        session.ended_at = now
        if session.started_at:
            delta = (now - session.started_at).total_seconds() / 60
            session.duration_minutes = round(delta, 1)

        return session.to_dict()
