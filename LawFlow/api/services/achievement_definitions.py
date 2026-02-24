"""Achievement catalog and seeding logic.

Each achievement has a key, display info, rarity, and tracking config.
Achievements are seeded into the DB on first run and checked on every
award_points() call.
"""

from api.models.rewards import Achievement
from api.services.database import get_db

# (key, title, description, icon, rarity, points, target)
ACHIEVEMENT_CATALOG = [
    # --- Common (easy wins for early engagement) ---
    ("first_exam",       "First Exam",         "Complete your first practice exam",       "file-check",    "common",    25,   1),
    ("first_upload",     "Data Contributor",    "Upload your first graded past test",      "upload",        "common",    50,   1),
    ("streak_3",         "Getting Started",     "Maintain a 3-day study streak",           "flame",         "common",    30,   3),

    # --- Uncommon (sustained effort) ---
    ("streak_7",         "Week Warrior",        "Maintain a 7-day study streak",           "flame",         "uncommon",  75,   7),
    ("exams_10",         "Exam Veteran",        "Complete 10 practice exams",              "clipboard-list","uncommon",  100,  10),
    ("flashcards_100",   "Card Shark",          "Review 100 flashcards",                   "layers",        "uncommon",  50,   100),
    ("mastery_first_80", "Subject Master",      "Get any topic to 80% mastery",            "star",          "uncommon",  75,   1),
    ("past_tests_5",     "Intel Gatherer",      "Upload 5 graded past tests",              "archive",       "uncommon",  150,  5),
    ("tutor_20",         "Socratic Scholar",    "Complete 20 tutor sessions",              "graduation-cap","uncommon",  100,  20),

    # --- Rare (serious dedication) ---
    ("streak_30",        "Iron Will",           "Maintain a 30-day study streak",          "shield",        "rare",      300,  30),
    ("exams_50",         "Exam Machine",        "Complete 50 practice exams",              "zap",           "rare",      250,  50),
    ("flashcards_1000",  "Memory Palace",       "Review 1,000 flashcards",                 "brain",         "rare",      200,  1000),
    ("mastery_all_50",   "Well-Rounded",        "Get all subjects above 50% mastery",      "compass",       "rare",      200,  1),
    ("past_tests_10",    "Exam Archaeologist",  "Upload 10 graded past tests",             "search",        "rare",      400,  10),

    # --- Legendary ---
    ("perfect_exam",     "Perfect Score",       "Score 100% on any practice exam",         "crown",         "legendary", 500,  1),
]

# Maps activity_type -> which achievement keys to check / increment
ACTIVITY_ACHIEVEMENT_MAP = {
    "exam_complete":      ["first_exam", "exams_10", "exams_50"],
    "flashcard_session":  ["flashcards_100", "flashcards_1000"],
    "tutor_session":      ["tutor_20"],
    "past_test_upload":   ["first_upload", "past_tests_5", "past_tests_10"],
}

# These are checked specially (not simple counters):
# - streak_3, streak_7, streak_30 -> checked in update_streak()
# - mastery_first_80, mastery_all_50 -> checked in check_mastery_achievements()
# - perfect_exam -> checked when exam score == 100


def seed_achievements(user_id: str | None = None):
    """Insert achievements that don't exist yet. Idempotent."""
    with get_db() as db:
        existing = {
            a.achievement_key
            for a in db.query(Achievement).filter_by(user_id=user_id).all()
        }
        added = 0
        for key, title, desc, icon, rarity, points, target in ACHIEVEMENT_CATALOG:
            if key not in existing:
                db.add(Achievement(
                    user_id=user_id,
                    achievement_key=key,
                    title=title,
                    description=desc,
                    icon=icon,
                    rarity=rarity,
                    points_awarded=points,
                    target_value=target,
                    current_value=0,
                ))
                added += 1
        if added:
            print(f"Seeded {added} new achievements.")
