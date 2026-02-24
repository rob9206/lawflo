"""Exam Analyzer — Claude reverse-engineers past exams to extract what topics are tested.

When a document with doc_type='exam' is uploaded, this service:
1. Sends the full exam text to Claude
2. Extracts: topics tested, weight per topic, question formats, professor patterns
3. Stores results in ExamBlueprint + ExamTopicWeight tables
4. This data drives the AutoTeach priority engine
"""

import json
import logging

import anthropic

from api.config import config
from api.services.claude_client import get_claude_client
from api.services.database import get_db
from api.models.document import Document, KnowledgeChunk
from api.models.exam_blueprint import ExamBlueprint, ExamTopicWeight

logger = logging.getLogger(__name__)

EXAM_ANALYSIS_PROMPT = """You are a law school exam analyst. Given the text of a past law school exam, analyze it thoroughly and extract structured data about what it tests.

Respond with ONLY a JSON object (no markdown fencing):
{
  "exam_title": "e.g. Contracts Final Fall 2024",
  "subject": "<primary subject: con_law, contracts, torts, crim_law, civ_pro, property, evidence, crim_pro, admin_law, prof_responsibility>",
  "exam_format": "<essay, mc, mixed, issue_spot>",
  "total_questions": <integer or null>,
  "time_limit_minutes": <integer or null if not stated>,
  "topics_tested": [
    {
      "topic": "<topic key matching our taxonomy, e.g. consideration, negligence_duty>",
      "weight": <0.0 to 1.0 — proportion of exam this topic covers>,
      "question_format": "<essay, mc, issue_spot, short_answer>",
      "difficulty": <0-100>,
      "notes": "How this topic tends to be tested — what angle the professor takes"
    }
  ],
  "professor_patterns": "Detected patterns: Does the professor favor policy questions? Multi-issue hypos? Trick MBE-style questions? Describe tendencies.",
  "high_yield_summary": "If a student could only study 5 things for this exam, what should they be? Be specific and actionable."
}

IMPORTANT:
- The topic keys should match standard law school taxonomy (e.g. 'consideration' not 'Consideration under Contract Law')
- Weights across all topics should sum to approximately 1.0
- Be specific about HOW each topic is tested, not just that it appears
- The high_yield_summary should be brutally practical — what would a tutor tell a cramming student

EXAM TEXT:
"""


def _get_client() -> anthropic.Anthropic:
    return get_claude_client()


def analyze_exam(document_id: str, user_id: str | None = None) -> dict:
    """Analyze a past exam document and create an ExamBlueprint.

    Returns the blueprint as a dict.
    """
    # Gather all text from the document's knowledge chunks
    with get_db() as db:
        doc = db.query(Document).filter_by(id=document_id, user_id=user_id).first()
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        chunks = (
            db.query(KnowledgeChunk)
            .filter_by(document_id=document_id, user_id=user_id)
            .order_by(KnowledgeChunk.chunk_index)
            .all()
        )

        if not chunks:
            raise ValueError(f"Document {document_id} has no processed chunks")

        exam_text = "\n\n---\n\n".join(c.content for c in chunks)
        doc_subject = doc.subject

    # Send to Claude for analysis
    client = _get_client()

    # Truncate if extremely long (keep within context budget)
    if len(exam_text) > 15000:
        exam_text = exam_text[:15000] + "\n\n[... remainder truncated for analysis]"

    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": EXAM_ANALYSIS_PROMPT + exam_text}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        analysis = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse exam analysis: {e}")
        raise ValueError("Claude returned invalid JSON for exam analysis")

    # Store in database
    with get_db() as db:
        # Remove existing blueprint for this document (re-analysis)
        db.query(ExamBlueprint).filter_by(document_id=document_id, user_id=user_id).delete()

        blueprint = ExamBlueprint(
            user_id=user_id,
            document_id=document_id,
            subject=analysis.get("subject", doc_subject or "other"),
            exam_title=analysis.get("exam_title"),
            exam_format=analysis.get("exam_format"),
            total_questions=analysis.get("total_questions"),
            time_limit_minutes=analysis.get("time_limit_minutes"),
            professor_patterns=analysis.get("professor_patterns"),
            high_yield_summary=analysis.get("high_yield_summary"),
        )
        db.add(blueprint)
        db.flush()

        for topic_data in analysis.get("topics_tested", []):
            weight = ExamTopicWeight(
                user_id=user_id,
                blueprint_id=blueprint.id,
                subject=analysis.get("subject", doc_subject or "other"),
                topic=topic_data["topic"],
                weight=topic_data.get("weight", 0.1),
                question_format=topic_data.get("question_format"),
                difficulty=topic_data.get("difficulty", 50),
                notes=topic_data.get("notes"),
            )
            db.add(weight)

        result = blueprint.to_dict()

    return result


def get_exam_blueprints(
    subject: str | None = None,
    user_id: str | None = None,
) -> list[dict]:
    """Get all exam blueprints, optionally filtered by subject."""
    with get_db() as db:
        query = db.query(ExamBlueprint).filter_by(user_id=user_id)
        if subject:
            query = query.filter_by(subject=subject)
        blueprints = query.order_by(ExamBlueprint.created_at.desc()).all()
        return [b.to_dict() for b in blueprints]


def get_aggregated_topic_weights(
    subject: str,
    user_id: str | None = None,
) -> dict[str, float]:
    """Aggregate topic weights across all exams for a subject.

    If multiple past exams exist, average the weights to get a
    composite picture of what's typically tested.

    Returns: {topic_key: average_weight}
    """
    with get_db() as db:
        weights = (
            db.query(ExamTopicWeight)
            .filter_by(user_id=user_id, subject=subject)
            .all()
        )

        if not weights:
            return {}

        # Aggregate: average weight per topic across all blueprints
        topic_sums: dict[str, list[float]] = {}
        for w in weights:
            if w.topic not in topic_sums:
                topic_sums[w.topic] = []
            topic_sums[w.topic].append(w.weight)

        return {
            topic: sum(vals) / len(vals)
            for topic, vals in topic_sums.items()
        }
