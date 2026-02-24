"""Rewards engine — the single entry point for all point-earning activities.

Every activity (exam, flashcard, tutor, upload) calls award_points().
This function handles: ledger entries, random bonuses, streak tracking,
achievement progress, and level calculation.
"""

import json
import logging
import random
from datetime import datetime, timezone

from sqlalchemy import func

from api.models.rewards import PointLedger, Achievement, RewardsProfile
from api.models.student import TopicMastery
from api.services.achievement_definitions import ACTIVITY_ACHIEVEMENT_MAP
from api.services.database import get_db

logger = logging.getLogger(__name__)

# Level thresholds: (min_points, level, title)
LEVEL_THRESHOLDS = [
    (25_000, 10, "Supreme Scholar"),
    (18_000,  9, "Distinguished Jurist"),
    (12_000,  8, "Partner"),
    (8_000,   7, "Senior Associate"),
    (5_000,   6, "Law Review Editor"),
    (3_000,   5, "Moot Court Champion"),
    (1_500,   4, "Case Expert"),
    (750,     3, "Legal Scholar"),
    (250,     2, "Diligent Student"),
    (0,       1, "Law Student"),
]

RANDOM_BONUS_CHANCE = 0.15
RANDOM_BONUS_MIN = 5
RANDOM_BONUS_MAX = 50


def award_points(
    activity_type: str,
    activity_id: str | None,
    description: str,
    base_amount: int,
    metadata: dict | None = None,
    user_id: str | None = None,
) -> dict:
    """Central point-awarding function. All point earning goes through here.

    Returns dict with: points_awarded, bonus, streak_info, new_balance,
    achievements_unlocked, level_up.
    """
    result = {
        "points_awarded": base_amount,
        "bonus": None,
        "streak_info": None,
        "new_balance": 0,
        "achievements_unlocked": [],
        "level_up": None,
    }

    try:
        with get_db() as db:
            # 1. Create base ledger entry
            db.add(PointLedger(
                user_id=user_id,
                amount=base_amount,
                activity_type=activity_type,
                activity_id=activity_id,
                description=description,
                metadata_json=json.dumps(metadata) if metadata else None,
            ))

            # 2. Roll for random bonus (15% chance)
            bonus = _roll_random_bonus()
            if bonus:
                result["bonus"] = bonus
                result["points_awarded"] += bonus
                db.add(PointLedger(
                    user_id=user_id,
                    amount=bonus,
                    activity_type="random_bonus",
                    activity_id=activity_id,
                    description=f"Lucky bonus! +{bonus}",
                    bonus_type="random_bonus",
                ))

            # 3. Update streak
            profile = _get_or_create_profile(db, user_id=user_id)
            streak_info = _update_streak(db, profile, user_id=user_id)
            result["streak_info"] = streak_info
            if streak_info and streak_info.get("bonus", 0) > 0:
                result["points_awarded"] += streak_info["bonus"]

            # 4. Check achievement progress
            unlocked = _check_achievements(db, activity_type, metadata or {}, user_id=user_id)
            result["achievements_unlocked"] = unlocked
            for ach in unlocked:
                result["points_awarded"] += ach["points_awarded"]

            # Check special achievements
            if activity_type == "exam_complete" and metadata and metadata.get("score") == 100:
                perfect = _try_unlock_achievement(db, "perfect_exam", user_id=user_id)
                if perfect:
                    result["achievements_unlocked"].append(perfect)
                    result["points_awarded"] += perfect["points_awarded"]

            # Check mastery achievements on exam completion
            if activity_type == "exam_complete":
                mastery_unlocks = _check_mastery_achievements(db, user_id=user_id)
                for ach in mastery_unlocks:
                    result["achievements_unlocked"].append(ach)
                    result["points_awarded"] += ach["points_awarded"]

            # 5. Update profile totals and level
            profile.total_earned += result["points_awarded"]
            old_level = profile.level
            new_level, new_title = _calculate_level(profile.total_earned)
            profile.level = new_level
            profile.active_title = new_title

            if new_level > old_level:
                result["level_up"] = {
                    "old_level": old_level,
                    "new_level": new_level,
                    "new_title": new_title,
                }

            db.flush()

            # 6. Compute balance
            result["new_balance"] = _get_balance(db, user_id=user_id)

    except Exception:
        logger.exception("Error awarding points for %s", activity_type)

    return result


def get_balance(user_id: str | None = None) -> int:
    """Current point balance (SUM of all ledger entries)."""
    with get_db() as db:
        return _get_balance(db, user_id=user_id)


def get_summary(user_id: str | None = None) -> dict:
    """Full rewards summary for dashboard/header."""
    with get_db() as db:
        profile = _get_or_create_profile(db, user_id=user_id)
        balance = _get_balance(db, user_id=user_id)

        # Level progress toward next level
        current_threshold = 0
        next_threshold = LEVEL_THRESHOLDS[0][0]  # max
        for pts, lvl, _ in LEVEL_THRESHOLDS:
            if lvl == profile.level:
                current_threshold = pts
                break
        for pts, lvl, _ in reversed(LEVEL_THRESHOLDS):
            if lvl == profile.level + 1:
                next_threshold = pts
                break

        if profile.level >= 10:
            level_progress = 1.0
        else:
            range_size = next_threshold - current_threshold
            progress_in_range = profile.total_earned - current_threshold
            level_progress = min(progress_in_range / range_size, 1.0) if range_size > 0 else 1.0

        # Recent transactions
        recent = (
            db.query(PointLedger)
            .filter_by(user_id=user_id)
            .order_by(PointLedger.created_at.desc())
            .limit(10)
            .all()
        )

        return {
            "balance": balance,
            "total_earned": profile.total_earned,
            "level": profile.level,
            "level_progress": round(level_progress, 3),
            "next_level_at": next_threshold if profile.level < 10 else None,
            "active_title": profile.active_title,
            "current_streak": profile.current_streak,
            "longest_streak": profile.longest_streak,
            "recent_transactions": [t.to_dict() for t in recent],
        }


def get_ledger(
    limit: int = 50,
    offset: int = 0,
    activity_type: str | None = None,
    user_id: str | None = None,
) -> dict:
    """Paginated point history."""
    with get_db() as db:
        query = db.query(PointLedger).filter_by(user_id=user_id)
        if activity_type:
            query = query.filter_by(activity_type=activity_type)

        total = query.count()
        entries = (
            query.order_by(PointLedger.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return {
            "entries": [e.to_dict() for e in entries],
            "total": total,
            "limit": limit,
            "offset": offset,
        }


def get_achievements(user_id: str | None = None) -> list[dict]:
    """All achievements with progress."""
    with get_db() as db:
        achievements = (
            db.query(Achievement)
            .filter_by(user_id=user_id)
            .order_by(
                Achievement.unlocked_at.desc().nullslast(),
                Achievement.rarity,
                Achievement.achievement_key,
            )
            .all()
        )
        return [a.to_dict() for a in achievements]


# ── Internal helpers ──────────────────────────────────────────────


def _get_or_create_profile(db, user_id: str | None = None) -> RewardsProfile:
    """Get or create the single rewards profile."""
    profile = db.query(RewardsProfile).filter_by(user_id=user_id).first()
    if not profile:
        profile = RewardsProfile(user_id=user_id)
        db.add(profile)
        db.flush()
    return profile


def _get_balance(db, user_id: str | None = None) -> int:
    """SUM of all ledger amounts."""
    result = db.query(func.sum(PointLedger.amount)).filter_by(user_id=user_id).scalar()
    return result or 0


def _roll_random_bonus() -> int | None:
    """15% chance of a random bonus between 5-50."""
    if random.random() < RANDOM_BONUS_CHANCE:
        return random.randint(RANDOM_BONUS_MIN, RANDOM_BONUS_MAX)
    return None


def _update_streak(db, profile: RewardsProfile, user_id: str | None = None) -> dict | None:
    """Update daily streak. Returns streak info + any bonus awarded."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if profile.last_active_date == today:
        # Already active today — no streak update
        return {"current_streak": profile.current_streak, "bonus": 0, "is_new_day": False}

    yesterday = None
    if profile.last_active_date:
        from datetime import timedelta
        last = datetime.strptime(profile.last_active_date, "%Y-%m-%d")
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    if profile.last_active_date == yesterday:
        # Consecutive day — extend streak
        profile.current_streak += 1
    else:
        # Streak broken (or first ever activity)
        profile.current_streak = 1

    profile.last_active_date = today
    if profile.current_streak > profile.longest_streak:
        profile.longest_streak = profile.current_streak

    # Streak bonus: 10 * min(streak, 7), caps at 70/day
    streak_bonus = 10 * min(profile.current_streak, 7)
    db.add(PointLedger(
        user_id=user_id,
        amount=streak_bonus,
        activity_type="streak_bonus",
        description=f"Day {profile.current_streak} streak bonus!",
        bonus_type="streak",
        metadata_json=json.dumps({"streak": profile.current_streak}),
    ))

    # Check streak achievements
    streak_achievements = {3: "streak_3", 7: "streak_7", 30: "streak_30"}
    streak_unlocks = []
    for threshold, key in streak_achievements.items():
        if profile.current_streak >= threshold:
            ach = _try_unlock_achievement(db, key, profile.current_streak, user_id=user_id)
            if ach:
                streak_unlocks.append(ach)

    return {
        "current_streak": profile.current_streak,
        "bonus": streak_bonus,
        "is_new_day": True,
        "achievements": streak_unlocks,
    }


def _check_achievements(
    db,
    activity_type: str,
    metadata: dict,
    user_id: str | None = None,
) -> list[dict]:
    """Check and update counter-based achievements for this activity type."""
    keys = ACTIVITY_ACHIEVEMENT_MAP.get(activity_type, [])
    unlocked = []

    for key in keys:
        ach = db.query(Achievement).filter_by(user_id=user_id, achievement_key=key).first()
        if not ach or ach.unlocked_at:
            continue

        # Increment counter
        if activity_type == "flashcard_session":
            # Flashcards count by cards_reviewed, not sessions
            ach.current_value += metadata.get("cards", 0)
        else:
            ach.current_value += 1

        # Check if target met
        if ach.current_value >= ach.target_value:
            ach.unlocked_at = datetime.now(timezone.utc)
            # Award achievement bonus
            db.add(PointLedger(
                user_id=user_id,
                amount=ach.points_awarded,
                activity_type="achievement_unlock",
                description=f"Achievement unlocked: {ach.title}",
                bonus_type="first_time",
                metadata_json=json.dumps({"achievement": key}),
            ))
            unlocked.append(ach.to_dict())

    return unlocked


def _try_unlock_achievement(
    db,
    key: str,
    value: int = 1,
    user_id: str | None = None,
) -> dict | None:
    """Try to unlock a specific achievement. Returns dict if newly unlocked."""
    ach = db.query(Achievement).filter_by(user_id=user_id, achievement_key=key).first()
    if not ach or ach.unlocked_at:
        return None

    ach.current_value = max(ach.current_value, value)
    if ach.current_value >= ach.target_value:
        ach.unlocked_at = datetime.now(timezone.utc)
        db.add(PointLedger(
            user_id=user_id,
            amount=ach.points_awarded,
            activity_type="achievement_unlock",
            description=f"Achievement unlocked: {ach.title}",
            bonus_type="first_time",
            metadata_json=json.dumps({"achievement": key}),
        ))
        return ach.to_dict()
    return None


def _check_mastery_achievements(db, user_id: str | None = None) -> list[dict]:
    """Check mastery-based achievements (topic hitting 80%, all above 50%)."""
    unlocked = []

    # mastery_first_80: any topic >= 80%
    ach_80 = db.query(Achievement).filter_by(
        user_id=user_id,
        achievement_key="mastery_first_80",
    ).first()
    if ach_80 and not ach_80.unlocked_at:
        high_mastery = db.query(TopicMastery).filter(
            TopicMastery.user_id == user_id,
            TopicMastery.mastery_score >= 80,
        ).first()
        if high_mastery:
            result = _try_unlock_achievement(db, "mastery_first_80", user_id=user_id)
            if result:
                unlocked.append(result)

    # mastery_all_50: all topics >= 50%
    ach_all = db.query(Achievement).filter_by(
        user_id=user_id,
        achievement_key="mastery_all_50",
    ).first()
    if ach_all and not ach_all.unlocked_at:
        topics = db.query(TopicMastery).filter_by(user_id=user_id).all()
        if topics and all(t.mastery_score >= 50 for t in topics):
            result = _try_unlock_achievement(db, "mastery_all_50", user_id=user_id)
            if result:
                unlocked.append(result)

    return unlocked


def _calculate_level(total_earned: int) -> tuple[int, str]:
    """Determine level and title from lifetime points."""
    for threshold, level, title in LEVEL_THRESHOLDS:
        if total_earned >= threshold:
            return level, title
    return 1, "Law Student"
