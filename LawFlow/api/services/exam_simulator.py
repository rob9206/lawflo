"""Exam Simulator — generates timed practice exams weighted by professor patterns.

Flow:
  1. generate_exam() → Creates Assessment + questions via Claude (weighted by priority engine)
  2. grade_answer()  → For MC: auto-grade. For essay: Claude IRAC rubric grading
  3. complete_exam() → Compute final score, update mastery, generate summary
"""

import json
import logging
from datetime import datetime, timezone

import anthropic

from api.config import config
from api.services.claude_client import get_claude_client
from api.services.database import get_db
from api.services.auto_teach import compute_priority
from api.services.exam_analyzer import get_aggregated_topic_weights, get_exam_blueprints
from api.models.assessment import Assessment, AssessmentQuestion
from api.models.student import SubjectMastery, TopicMastery
from api.models.document import KnowledgeChunk

logger = logging.getLogger(__name__)


# ── IRAC Grading Weights ────────────────────────────────────────────────────
#
# How much each IRAC component contributes to the overall essay score.
# These weights shape the entire grading experience.
#
# Trade-offs to consider:
#   - Issue spotting is the #1 differentiator on law school exams.
#     Missing an issue = missing all points for that issue's analysis.
#     Weight it heavily.
#   - Rule statement is necessary but not sufficient.
#     Students who state rules without applying them don't score well.
#   - Application is where the points live — using specific facts
#     from the hypo, arguing both sides, showing legal reasoning.
#   - Conclusion matters least — professors care about the analysis
#     more than the answer. A wrong conclusion with great analysis
#     scores higher than right conclusion with no analysis.
#
IRAC_WEIGHTS = {
    "issue_spotting": 0.30,
    "rule_accuracy": 0.20,
    "application_depth": 0.35,
    "conclusion_support": 0.15,
}


# ── Claude Prompts ──────────────────────────────────────────────────────────

QUESTION_GENERATION_PROMPT = """You are a law school exam question writer. Generate exam questions for a practice exam.

SUBJECT: {subject}
EXAM FORMAT REQUESTED: {format}
NUMBER OF QUESTIONS: {num_questions}

{exam_context}

{knowledge_context}

TOPIC DISTRIBUTION (generate questions proportional to these weights):
{topic_distribution}

RULES:
- Generate exactly {num_questions} questions
- Match the question formats specified in the topic distribution when available
- For essay questions: write realistic fact patterns (hypos) with multiple embedded legal issues
- For MC questions: write 4 options (A-D) with one clearly best answer, use MBE-style complexity
- For issue_spot questions: write fact patterns and ask the student to identify all legal issues
- Each question must specify which topic it tests and its difficulty (0-100)
- Difficulty should vary: mix easy rule-recall with hard multi-issue analysis
- Make questions exam-realistic — the kind a law professor would actually write

Respond with ONLY a JSON array (no markdown fencing):
[
  {{
    "question_type": "essay" | "mc" | "issue_spot",
    "question_text": "The full question or fact pattern",
    "options": ["A) ...", "B) ...", "C) ...", "D) ..."] | null,
    "correct_answer": "For MC: the letter. For essay/issue_spot: model answer outline",
    "topic": "topic_key matching taxonomy",
    "difficulty": 0-100
  }}
]
"""

ESSAY_GRADING_PROMPT = """You are a law school professor grading an exam essay using the IRAC method.

QUESTION:
{question}

STUDENT'S ANSWER:
{answer}

MODEL ANSWER OUTLINE (for reference — the student doesn't need to match this exactly):
{model_answer}

GRADE this essay on four IRAC components, each scored 0-100:

1. **Issue Spotting** (weight: 30%): Did the student identify all relevant legal issues?
   - 90-100: Found all major and minor issues
   - 70-89: Found all major issues, missed some minor ones
   - 50-69: Found most major issues
   - 30-49: Missed significant issues
   - 0-29: Failed to identify the core legal issues

2. **Rule Accuracy** (weight: 20%): Did the student correctly state the applicable legal rules?
   - 90-100: Rules stated accurately with proper elements/factors
   - 70-89: Rules mostly correct with minor omissions
   - 50-69: Basic rules stated but missing key elements
   - 30-49: Significant rule errors
   - 0-29: Rules incorrect or absent

3. **Application Depth** (weight: 35%): Did the student apply rules to specific facts?
   - 90-100: Thorough application using specific facts, argued both sides
   - 70-89: Good application with most relevant facts, some counterarguments
   - 50-69: Applied rules but missed key facts or only argued one side
   - 30-49: Conclusory application without using specific facts
   - 0-29: No meaningful application

4. **Conclusion Support** (weight: 15%): Is the conclusion supported by the analysis?
   - 90-100: Logical conclusion flowing from analysis
   - 70-89: Reasonable conclusion with adequate support
   - 50-69: Conclusion present but weakly supported
   - 30-49: Conclusion contradicts analysis or is unsupported
   - 0-29: No conclusion or completely disconnected

Respond with ONLY a JSON object (no markdown fencing):
{{
  "issue_spotting": <0-100>,
  "rule_accuracy": <0-100>,
  "application_depth": <0-100>,
  "conclusion_support": <0-100>,
  "overall_score": <weighted average>,
  "issues_found": ["list of issues the student identified"],
  "issues_missed": ["list of issues the student missed"],
  "strengths": "What the student did well (1-2 sentences)",
  "weaknesses": "Where to improve (1-2 sentences)",
  "feedback": "Detailed paragraph of feedback with specific suggestions"
}}
"""

ISSUE_SPOT_GRADING_PROMPT = """You are a law school professor grading an issue-spotting exercise.

QUESTION:
{question}

STUDENT'S ANSWER:
{answer}

MODEL ANSWER (all issues that should be spotted):
{model_answer}

Evaluate how many legal issues the student correctly identified.

Respond with ONLY a JSON object (no markdown fencing):
{{
  "issues_found": ["list of issues correctly identified"],
  "issues_missed": ["list of issues the student missed"],
  "false_positives": ["issues the student raised that aren't relevant"],
  "score": <0-100 based on proportion of issues found>,
  "feedback": "Brief feedback on issue-spotting performance"
}}
"""


# ── Service Functions ───────────────────────────────────────────────────────

def _get_client() -> anthropic.Anthropic:
    return get_claude_client()


def generate_exam(
    subject: str,
    exam_format: str = "mixed",
    num_questions: int = 5,
    time_minutes: int = 60,
    user_id: str | None = None,
) -> dict:
    """Generate a complete practice exam weighted by exam blueprint + mastery gaps.

    Returns the Assessment dict with all questions included.
    """
    # Get topic weights and mastery data
    exam_weights = get_aggregated_topic_weights(subject, user_id=user_id)
    has_exam_data = bool(exam_weights)

    with get_db() as db:
        topics = db.query(TopicMastery).filter_by(user_id=user_id, subject=subject).all()
        if not topics:
            raise ValueError(f"No topics found for {subject}. Run seed script first.")

        subject_record = db.query(SubjectMastery).filter_by(user_id=user_id, subject=subject).first()

    # Compute priority scores for topic weighting
    default_weight = 1.0 / len(topics) if topics else 0.1
    topic_priorities = []
    for t in topics:
        w = exam_weights.get(t.topic, default_weight)
        priority = compute_priority(w, t.mastery_score)
        topic_priorities.append({
            "topic": t.topic,
            "display_name": t.display_name,
            "weight": w,
            "mastery": t.mastery_score,
            "priority": priority,
        })

    # Sort by priority — highest priority topics get more questions
    topic_priorities.sort(key=lambda x: x["priority"], reverse=True)

    # Build topic distribution string for the prompt
    top_topics = topic_priorities[:min(num_questions * 2, len(topic_priorities))]
    distribution_lines = []
    for tp in top_topics:
        fmt = ""
        if has_exam_data:
            # Find question format from blueprint
            blueprints = get_exam_blueprints(subject, user_id=user_id)
            if blueprints:
                for tw in blueprints[0].get("topics_tested", []):
                    if tw["topic"] == tp["topic"]:
                        fmt = f" (professor tests as: {tw.get('question_format', 'essay')})"
                        break
        distribution_lines.append(
            f"- {tp['display_name']} ({tp['topic']}): "
            f"exam_weight={tp['weight']:.2f}, student_mastery={tp['mastery']:.0f}%, "
            f"priority={tp['priority']:.3f}{fmt}"
        )

    # Build exam context from blueprints
    exam_context_str = ""
    if has_exam_data:
        blueprints = get_exam_blueprints(subject, user_id=user_id)
        if blueprints:
            bp = blueprints[0]
            exam_context_str = (
                f"PROFESSOR PATTERNS (from past exam analysis):\n"
                f"Format: {bp.get('exam_format', 'unknown')}\n"
                f"Patterns: {bp.get('professor_patterns', 'None detected')}\n"
                f"High-yield topics: {bp.get('high_yield_summary', 'N/A')}\n"
            )

    # Get relevant knowledge chunks for context
    knowledge_str = ""
    with get_db() as db:
        chunks = (
            db.query(KnowledgeChunk)
            .filter(
                KnowledgeChunk.user_id == user_id,
                KnowledgeChunk.subject == subject,
            )
            .limit(8)
            .all()
        )
        if chunks:
            knowledge_str = "RELEVANT COURSE MATERIAL (use to inform question content):\n"
            for c in chunks:
                knowledge_str += f"[{c.topic}] {c.content[:500]}\n---\n"

    # Generate questions via Claude
    prompt = QUESTION_GENERATION_PROMPT.format(
        subject=subject,
        format=exam_format,
        num_questions=num_questions,
        exam_context=exam_context_str,
        knowledge_context=knowledge_str,
        topic_distribution="\n".join(distribution_lines),
    )

    client = _get_client()
    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        questions_data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse exam questions: {e}")
        raise ValueError("Claude returned invalid JSON for exam questions")

    # Store assessment and questions
    with get_db() as db:
        topics_list = list({q.get("topic", "") for q in questions_data})

        assessment = Assessment(
            user_id=user_id,
            assessment_type=exam_format,
            subject=subject,
            topics=json.dumps(topics_list),
            total_questions=len(questions_data),
            time_limit_minutes=time_minutes,
            is_timed=1 if time_minutes > 0 else 0,
        )
        db.add(assessment)
        db.flush()

        for i, q_data in enumerate(questions_data):
            question = AssessmentQuestion(
                user_id=user_id,
                assessment_id=assessment.id,
                question_index=i,
                question_type=q_data.get("question_type", "essay"),
                question_text=q_data["question_text"],
                options=json.dumps(q_data.get("options")) if q_data.get("options") else None,
                correct_answer=q_data.get("correct_answer"),
                subject=subject,
                topic=q_data.get("topic"),
                difficulty=q_data.get("difficulty", 50),
            )
            db.add(question)

        db.flush()

        result = assessment.to_dict()
        result["questions"] = [q.to_dict() for q in assessment.questions]

    return result


def grade_answer(
    question_id: str,
    student_answer: str,
    user_id: str | None = None,
) -> dict:
    """Grade a single answer. MC is auto-graded; essay/issue_spot uses Claude."""
    with get_db() as db:
        question = db.query(AssessmentQuestion).filter_by(id=question_id, user_id=user_id).first()
        if not question:
            raise ValueError(f"Question {question_id} not found")

        question.student_answer = student_answer
        q_type = question.question_type
        q_text = question.question_text
        model_answer = question.correct_answer or ""
        options = json.loads(question.options) if question.options else None

    if q_type == "mc":
        return _grade_mc(question_id, student_answer, model_answer, options, user_id=user_id)
    elif q_type == "issue_spot":
        return _grade_issue_spot(
            question_id,
            q_text,
            student_answer,
            model_answer,
            user_id=user_id,
        )
    else:
        return _grade_essay(
            question_id,
            q_text,
            student_answer,
            model_answer,
            user_id=user_id,
        )


def _grade_mc(
    question_id: str,
    answer: str,
    correct: str,
    options: list | None,
    user_id: str | None = None,
) -> dict:
    """Auto-grade a multiple choice question."""
    # Normalize: extract just the letter
    answer_letter = answer.strip().upper()[:1]
    correct_letter = correct.strip().upper()[:1]

    is_correct = answer_letter == correct_letter
    score = 100.0 if is_correct else 0.0

    feedback = f"{'Correct!' if is_correct else f'Incorrect. The correct answer is {correct_letter}.'}"
    if not is_correct and correct:
        feedback += f"\n\nExplanation: {correct}"

    with get_db() as db:
        q = db.query(AssessmentQuestion).filter_by(id=question_id, user_id=user_id).first()
        q.student_answer = answer
        q.is_correct = 1 if is_correct else 0
        q.score = score
        q.feedback = feedback
        db.flush()
        return q.to_dict()


def _grade_essay(
    question_id: str,
    question_text: str,
    answer: str,
    model_answer: str,
    user_id: str | None = None,
) -> dict:
    """Grade an essay question using Claude IRAC rubric."""
    if not answer or len(answer.strip()) < 10:
        with get_db() as db:
            q = db.query(AssessmentQuestion).filter_by(id=question_id, user_id=user_id).first()
            q.student_answer = answer
            q.score = 0.0
            q.feedback = json.dumps({
                "issue_spotting": 0, "rule_accuracy": 0,
                "application_depth": 0, "conclusion_support": 0,
                "overall_score": 0,
                "feedback": "No substantive answer provided.",
            })
            db.flush()
            return q.to_dict()

    prompt = ESSAY_GRADING_PROMPT.format(
        question=question_text,
        answer=answer,
        model_answer=model_answer or "(No model answer available — grade based on legal accuracy)",
    )

    client = _get_client()
    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        grading = json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse essay grading for {question_id}")
        grading = {
            "issue_spotting": 50, "rule_accuracy": 50,
            "application_depth": 50, "conclusion_support": 50,
            "overall_score": 50,
            "feedback": "Grading failed — could not parse AI response.",
        }

    # Compute weighted score
    weighted_score = (
        grading.get("issue_spotting", 50) * IRAC_WEIGHTS["issue_spotting"]
        + grading.get("rule_accuracy", 50) * IRAC_WEIGHTS["rule_accuracy"]
        + grading.get("application_depth", 50) * IRAC_WEIGHTS["application_depth"]
        + grading.get("conclusion_support", 50) * IRAC_WEIGHTS["conclusion_support"]
    )
    grading["overall_score"] = round(weighted_score, 1)

    with get_db() as db:
        q = db.query(AssessmentQuestion).filter_by(id=question_id, user_id=user_id).first()
        q.student_answer = answer
        q.score = weighted_score
        q.feedback = json.dumps(grading)
        db.flush()
        return q.to_dict()


def _grade_issue_spot(
    question_id: str,
    question_text: str,
    answer: str,
    model_answer: str,
    user_id: str | None = None,
) -> dict:
    """Grade an issue-spotting exercise using Claude."""
    if not answer or len(answer.strip()) < 10:
        with get_db() as db:
            q = db.query(AssessmentQuestion).filter_by(id=question_id, user_id=user_id).first()
            q.student_answer = answer
            q.score = 0.0
            q.feedback = json.dumps({
                "score": 0,
                "issues_found": [],
                "issues_missed": [],
                "feedback": "No substantive answer provided.",
            })
            db.flush()
            return q.to_dict()

    prompt = ISSUE_SPOT_GRADING_PROMPT.format(
        question=question_text,
        answer=answer,
        model_answer=model_answer or "(Grade based on standard legal analysis)",
    )

    client = _get_client()
    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        grading = json.loads(text)
    except json.JSONDecodeError:
        grading = {"score": 50, "issues_found": [], "issues_missed": [], "feedback": "Grading parse error."}

    with get_db() as db:
        q = db.query(AssessmentQuestion).filter_by(id=question_id, user_id=user_id).first()
        q.student_answer = answer
        q.score = float(grading.get("score", 50))
        q.feedback = json.dumps(grading)
        db.flush()
        return q.to_dict()


def complete_exam(assessment_id: str, user_id: str | None = None) -> dict:
    """Finalize an exam — compute overall score, update mastery, generate summary.

    Returns the complete results dict.
    """
    with get_db() as db:
        assessment = db.query(Assessment).filter_by(id=assessment_id, user_id=user_id).first()
        if not assessment:
            raise ValueError(f"Assessment {assessment_id} not found")

        questions = (
            db.query(AssessmentQuestion)
            .filter_by(assessment_id=assessment_id, user_id=user_id)
            .order_by(AssessmentQuestion.question_index)
            .all()
        )

        # Compute overall score
        scored = [q for q in questions if q.score is not None]
        if scored:
            overall = sum(q.score for q in scored) / len(scored)
        else:
            overall = 0.0

        assessment.score = round(overall, 1)
        assessment.completed_at = datetime.now(timezone.utc)

        # Compute time taken — normalize created_at to UTC-aware since SQLite
        # returns offset-naive datetimes while completed_at is offset-aware
        if assessment.created_at:
            created = assessment.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            delta = (assessment.completed_at - created).total_seconds() / 60
            assessment.time_taken_minutes = round(delta, 1)

        # Generate per-topic breakdown
        topic_scores: dict[str, list[float]] = {}
        for q in questions:
            if q.topic and q.score is not None:
                topic_scores.setdefault(q.topic, []).append(q.score)

        topic_breakdown = {
            topic: round(sum(scores) / len(scores), 1)
            for topic, scores in topic_scores.items()
        }

        # Build feedback summary
        weak_topics = [t for t, s in topic_breakdown.items() if s < 60]
        strong_topics = [t for t, s in topic_breakdown.items() if s >= 80]

        summary_parts = [f"Overall score: {overall:.1f}/100."]
        if strong_topics:
            summary_parts.append(f"Strong areas: {', '.join(strong_topics)}.")
        if weak_topics:
            summary_parts.append(f"Needs work: {', '.join(weak_topics)}.")

        assessment.feedback_summary = " ".join(summary_parts)
        db.flush()

        # Update mastery scores based on exam performance
        _update_mastery_from_exam(assessment.subject, topic_scores, db, user_id=user_id)

        result = assessment.to_dict()
        result["questions"] = [q.to_dict() for q in questions]
        result["topic_breakdown"] = topic_breakdown

        # Award points for exam completion
        try:
            from api.services.rewards_engine import award_points
            reward = award_points(
                "exam_complete", assessment_id,
                f"Completed {assessment.subject} exam ({assessment.score:.0f}%)",
                base_amount=50 + int(assessment.score / 2),
                metadata={"subject": assessment.subject, "score": assessment.score},
                user_id=user_id,
            )
            result["points_awarded"] = reward
        except Exception:
            pass  # Don't break exam flow if rewards fail

    return result


def _update_mastery_from_exam(
    subject: str,
    topic_scores: dict[str, list[float]],
    db,
    user_id: str | None = None,
):
    """Update mastery scores based on exam performance.

    Exam results are a strong signal — a 90% score on an exam question
    is more reliable than a single flashcard review. We weight exam
    performance more heavily in mastery updates.

    Accepts an existing db session to avoid nested transactions (SQLite
    only allows one writer at a time, so opening a second session while
    the caller's transaction is still open causes a "database is locked" 500).
    """
    for topic_name, scores in topic_scores.items():
        avg_score = sum(scores) / len(scores)

        topic = db.query(TopicMastery).filter_by(
            user_id=user_id, subject=subject, topic=topic_name
        ).first()
        if not topic:
            continue

        # Exam-weighted mastery update
        # Blend current mastery with exam score (exam gets 40% weight)
        new_mastery = topic.mastery_score * 0.6 + avg_score * 0.4
        topic.mastery_score = max(0, min(100, new_mastery))
        topic.exposure_count += len(scores)
        topic.last_studied_at = datetime.now(timezone.utc)

        # Count correct/incorrect
        for s in scores:
            if s >= 60:
                topic.correct_count += 1
            else:
                topic.incorrect_count += 1

    # Update subject-level mastery
    subj = db.query(SubjectMastery).filter_by(user_id=user_id, subject=subject).first()
    if subj:
        all_topics = db.query(TopicMastery).filter_by(user_id=user_id, subject=subject).all()
        if all_topics:
            subj.mastery_score = sum(t.mastery_score for t in all_topics) / len(all_topics)
        subj.assessments_count += 1
        subj.last_studied_at = datetime.now(timezone.utc)


def get_exam_results(assessment_id: str, user_id: str | None = None) -> dict | None:
    """Get full exam results with questions and grading details."""
    with get_db() as db:
        assessment = db.query(Assessment).filter_by(id=assessment_id, user_id=user_id).first()
        if not assessment:
            return None

        questions = (
            db.query(AssessmentQuestion)
            .filter_by(assessment_id=assessment_id, user_id=user_id)
            .order_by(AssessmentQuestion.question_index)
            .all()
        )

        result = assessment.to_dict()
        result["questions"] = []

        topic_scores: dict[str, list[float]] = {}
        irac_totals = {"issue_spotting": [], "rule_accuracy": [], "application_depth": [], "conclusion_support": []}

        for q in questions:
            q_dict = q.to_dict()
            # Parse feedback JSON for IRAC breakdown
            if q.feedback:
                try:
                    q_dict["grading"] = json.loads(q.feedback)
                    # Aggregate IRAC scores for essays
                    if q.question_type == "essay":
                        g = q_dict["grading"]
                        for key in irac_totals:
                            if key in g:
                                irac_totals[key].append(g[key])
                except json.JSONDecodeError:
                    q_dict["grading"] = None

            if q.topic and q.score is not None:
                topic_scores.setdefault(q.topic, []).append(q.score)

            result["questions"].append(q_dict)

        result["topic_breakdown"] = {
            topic: round(sum(scores) / len(scores), 1)
            for topic, scores in topic_scores.items()
        }

        # Aggregate IRAC scores across all essays
        result["irac_breakdown"] = {
            key: round(sum(vals) / len(vals), 1) if vals else None
            for key, vals in irac_totals.items()
        }

        return result


def get_exam_history(
    subject: str | None = None,
    limit: int = 10,
    user_id: str | None = None,
) -> list[dict]:
    """Get past exam attempts."""
    with get_db() as db:
        query = db.query(Assessment).filter(
            Assessment.user_id == user_id,
            Assessment.completed_at.isnot(None),
        )
        if subject:
            query = query.filter_by(subject=subject)
        exams = query.order_by(Assessment.completed_at.desc()).limit(limit).all()
        return [e.to_dict() for e in exams]
