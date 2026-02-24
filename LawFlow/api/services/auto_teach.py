"""AutoTeach Orchestrator — the brain that decides WHAT to teach and HOW.

This is the core intelligence that transforms LawFlow from a chatbot into a tutor.
It combines three data sources:
  1. Exam blueprints (what topics are tested, how heavily)
  2. Student mastery (what the student knows and doesn't)
  3. Pedagogical rules (which teaching mode works best at each mastery level)

The output is a prioritized teaching plan: ordered list of topics with the
optimal teaching mode for each, based on exam weight × knowledge gap.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from api.services.database import get_db
from api.services.exam_analyzer import get_aggregated_topic_weights
from api.models.student import SubjectMastery, TopicMastery
from api.models.document import KnowledgeChunk

logger = logging.getLogger(__name__)


@dataclass
class TeachingTarget:
    """A single topic the student should study, with context."""
    subject: str
    topic: str
    display_name: str
    priority_score: float        # Higher = study this first
    mastery: float               # Current mastery 0-100
    exam_weight: float           # How much of the exam tests this (0-1)
    recommended_mode: str        # Which tutor mode to use
    mode_reason: str             # Why this mode was chosen
    knowledge_chunks_available: int  # How many chunks we have on this topic
    time_estimate_minutes: int   # Estimated study time needed

    def to_dict(self) -> dict:
        return {
            "subject": self.subject,
            "topic": self.topic,
            "display_name": self.display_name,
            "priority_score": round(self.priority_score, 3),
            "mastery": round(self.mastery, 1),
            "exam_weight": round(self.exam_weight, 3),
            "recommended_mode": self.recommended_mode,
            "mode_reason": self.mode_reason,
            "knowledge_chunks_available": self.knowledge_chunks_available,
            "time_estimate_minutes": self.time_estimate_minutes,
        }


def compute_priority(exam_weight: float, mastery: float) -> float:
    """Compute study priority for a topic.

    This is the core optimization function. Higher score = study this first.

    Args:
        exam_weight: How much of the exam tests this topic (0.0 - 1.0).
                     If no exam data exists, defaults to equal weight.
        mastery: Student's current mastery of this topic (0 - 100).

    Returns:
        Priority score (higher = more urgent to study).

    ────────────────────────────────────────────────────────────
    TODO: This function is where YOUR learning strategy lives.

    The current implementation uses a simple formula, but you might
    want to tune it. Consider these trade-offs:

    - Linear gap (1 - mastery/100) treats going from 0→20 the same
      as going from 80→100. But in practice, the first 20% of
      understanding yields MORE exam points than the last 20%.

    - Should a topic with 0.3 exam weight and 10% mastery outrank
      a topic with 0.1 weight and 0% mastery? The current formula
      says yes (0.27 vs 0.10). Is that right for your exams?

    - Some students benefit from a "minimum competency first" approach:
      get every topic to 40% before pushing any to 80%.
      Others benefit from "depth first": master one topic completely
      before moving on. Which matches how you learn?

    Alternative approaches to consider:
      - Diminishing returns: priority = exam_weight * (1 - mastery/100) ** 0.5
      - Threshold boost:  add bonus priority if mastery < 20 (critical gap)
      - Recency penalty:  lower priority if studied recently (avoid burnout)
    ────────────────────────────────────────────────────────────
    """
    knowledge_gap = 1.0 - (mastery / 100.0)
    return exam_weight * knowledge_gap


def select_teaching_mode(mastery: float, has_exam_data: bool) -> tuple[str, str]:
    """Select the optimal teaching mode based on current mastery level.

    Returns (mode_key, reason) explaining why this mode was chosen.

    The logic follows cognitive science principles:
    - You can't probe understanding of something they haven't learned yet
    - You can't do exam simulation until they know the rules
    - Each mode is optimal within a mastery band
    """
    if mastery < 15:
        return "explain", "Near-zero knowledge — need foundational concepts first (compressed teaching)"
    elif mastery < 35:
        return "explain", "Low mastery — building core knowledge before testing understanding"
    elif mastery < 55:
        return "socratic", "Moderate base — probing understanding to find and fill specific gaps"
    elif mastery < 75:
        return "hypo", "Solid base — testing rule boundaries with fact variations"
    elif mastery < 90:
        if has_exam_data:
            return "issue_spot", "Strong knowledge — exam-style issue spotting for test readiness"
        else:
            return "irac", "Strong knowledge — structured analysis practice"
    else:
        return "irac", "Near-mastery — full IRAC exam simulation to polish performance"


def generate_teaching_plan(
    subject: str,
    max_topics: int = 10,
    available_minutes: int | None = None,
    user_id: str | None = None,
) -> dict:
    """Generate a prioritized teaching plan for a subject.

    Combines exam weight data (if available) with mastery gaps
    to produce an ordered list of what to study and how.

    Args:
        subject: The law subject to plan for
        max_topics: Maximum topics to include in the plan
        available_minutes: If set, limits plan to fit within time budget

    Returns:
        Dict with teaching_plan (ordered targets), metadata, and
        auto_session config for the highest-priority topic.
    """
    # Get exam weights (empty dict if no exams uploaded for this subject)
    exam_weights = get_aggregated_topic_weights(subject, user_id=user_id)
    has_exam_data = bool(exam_weights)

    with get_db() as db:
        # Get all topics for this subject with mastery data
        topics = db.query(TopicMastery).filter_by(user_id=user_id, subject=subject).all()

        subject_record = db.query(SubjectMastery).filter_by(user_id=user_id, subject=subject).first()
        subject_display = subject_record.display_name if subject_record else subject

        if not topics:
            return {
                "subject": subject,
                "subject_display": subject_display,
                "has_exam_data": False,
                "teaching_plan": [],
                "total_estimated_minutes": 0,
                "auto_session": None,
                "message": (
                    f"No topics found for {subject}. "
                    "Restart the backend to run the seed (subjects/topics are seeded on startup)."
                ),
            }

        # Count available knowledge chunks per topic
        chunk_counts = {}
        for t in topics:
            count = (
                db.query(KnowledgeChunk)
                .filter_by(user_id=user_id, subject=subject, topic=t.topic)
                .count()
            )
            chunk_counts[t.topic] = count

    # Build teaching targets
    targets: list[TeachingTarget] = []

    # If we have exam data, use those weights
    # If not, give all topics equal weight
    default_weight = 1.0 / len(topics) if topics else 0.1

    for t in topics:
        exam_weight = exam_weights.get(t.topic, default_weight)
        priority = compute_priority(exam_weight, t.mastery_score)
        mode, reason = select_teaching_mode(t.mastery_score, has_exam_data)

        # Estimate study time based on mastery gap
        # Rule of thumb: ~5 min per 10% of mastery gap
        gap = 100 - t.mastery_score
        time_est = max(5, int(gap * 0.5))

        targets.append(TeachingTarget(
            subject=subject,
            topic=t.topic,
            display_name=t.display_name,
            priority_score=priority,
            mastery=t.mastery_score,
            exam_weight=exam_weight,
            recommended_mode=mode,
            mode_reason=reason,
            knowledge_chunks_available=chunk_counts.get(t.topic, 0),
            time_estimate_minutes=time_est,
        ))

    # Sort by priority (highest first)
    targets.sort(key=lambda t: t.priority_score, reverse=True)

    # Trim to max_topics
    targets = targets[:max_topics]

    # If time-constrained, trim to fit within budget
    if available_minutes:
        fitted = []
        remaining = available_minutes
        for t in targets:
            if remaining <= 0:
                break
            fitted.append(t)
            remaining -= t.time_estimate_minutes
        targets = fitted

    # Build auto-session config for the highest-priority topic
    auto_session = None
    if targets:
        top = targets[0]
        auto_session = {
            "mode": top.recommended_mode,
            "subject": subject,
            "topics": [top.topic],
            "opening_message": _build_opening_message(top, has_exam_data, available_minutes),
        }

    return {
        "subject": subject,
        "subject_display": subject_display,
        "has_exam_data": has_exam_data,
        "teaching_plan": [t.to_dict() for t in targets],
        "total_estimated_minutes": sum(t.time_estimate_minutes for t in targets),
        "auto_session": auto_session,
    }


def _build_opening_message(
    target: TeachingTarget,
    has_exam_data: bool,
    available_minutes: int | None = None,
) -> str:
    """Build the first message to send to the tutor on behalf of the student.

    This is what kicks off the auto-teach session — the system sends this
    as the 'user' message so the tutor immediately starts teaching the
    right thing in the right way.
    """
    parts = [f"Teach me about {target.display_name} in {target.subject}."]
    parts.append(f"My current mastery is {target.mastery:.0f}%.")

    if has_exam_data:
        parts.append(
            f"This topic accounts for ~{target.exam_weight*100:.0f}% of my exam."
        )

    if available_minutes:
        parts.append(f"I have {available_minutes} minutes to study.")
        if available_minutes <= 30:
            parts.append("Keep it ultra-compressed — only the highest-yield material.")
        elif available_minutes <= 60:
            parts.append("Standard depth — cover the core rules, one case example, and key traps.")
        elif available_minutes <= 90:
            parts.append("I have extra time — include edge cases and competing arguments.")
        else:
            parts.append("Deep dive — give me full treatment with multiple cases, policy rationale, and exam strategy.")

    if target.mastery < 20:
        parts.append("I'm starting nearly from scratch — give me the fundamentals.")
    elif target.mastery < 50:
        parts.append("I have some basics but significant gaps. Focus on what I'm missing.")
    elif target.mastery < 75:
        parts.append("I know the basics — test my understanding and push me on edge cases.")
    else:
        parts.append("I'm fairly strong here — give me exam-level practice and catch any blind spots.")

    return " ".join(parts)


def get_next_topic(
    subject: str,
    available_minutes: int | None = None,
    user_id: str | None = None,
) -> dict | None:
    """Quick helper: get just the single highest-priority topic to study next.

    Useful for a "What should I study right now?" button.
    """
    plan = generate_teaching_plan(
        subject,
        max_topics=1,
        available_minutes=available_minutes,
        user_id=user_id,
    )
    if plan["teaching_plan"]:
        return {
            **plan["teaching_plan"][0],
            "auto_session": plan["auto_session"],
        }
    return None
