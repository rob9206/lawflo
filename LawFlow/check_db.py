import sqlite3

conn = sqlite3.connect("data/lawflow.db")
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM topic_mastery WHERE exposure_count IS NULL OR correct_count IS NULL OR incorrect_count IS NULL")
print("topic_mastery with NULL counts:", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM subject_mastery WHERE sessions_count IS NULL OR assessments_count IS NULL OR total_study_time_minutes IS NULL")
print("subject_mastery with NULL counts:", cur.fetchone()[0])

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("Tables:", tables)

if "assessments" in tables:
    cur.execute("SELECT COUNT(*) FROM assessments")
    print("Assessments:", cur.fetchone()[0])
    cur.execute("PRAGMA table_info(assessments)")
    for c in cur.fetchall():
        print(f"  {c[1]} ({c[2]}) default={c[4]}")

if "assessment_questions" in tables:
    cur.execute("SELECT COUNT(*) FROM assessment_questions")
    print("Assessment questions:", cur.fetchone()[0])

# Check profile table for NULL issues
if "student_profiles" in tables:
    cur.execute("PRAGMA table_info(student_profiles)")
    print("Profile columns:")
    for c in cur.fetchall():
        print(f"  {c[1]} ({c[2]}) default={c[4]}")
    cur.execute("SELECT COUNT(*) FROM student_profiles")
    print("Profiles:", cur.fetchone()[0])
    cur.execute("SELECT * FROM student_profiles LIMIT 1")
    row = cur.fetchone()
    if row:
        print("First profile:", row)

conn.close()
