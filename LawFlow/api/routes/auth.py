"""Authentication and user profile routes."""

import re

import bcrypt
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from api.errors import UnauthorizedError, ValidationError
from api.middleware.auth import (
    decode_token,
    get_current_user,
    get_current_user_id,
    issue_auth_tokens,
    login_required,
)
from api.models.assessment import Assessment, AssessmentQuestion
from api.models.document import Document, KnowledgeChunk
from api.models.exam_blueprint import ExamBlueprint, ExamTopicWeight
from api.models.rewards import Achievement, PointLedger, RewardsProfile
from api.models.review import SpacedRepetitionCard
from api.models.session import SessionMessage, StudySession
from api.models.student import SubjectMastery, TopicMastery
from api.models.study_plan import PlanTask, StudyPlan
from api.models.user import User
from api.services.achievement_definitions import seed_achievements
from api.services.database import get_db
from api.services.subject_taxonomy import seed_subject_taxonomy

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_email(value: str) -> str:
    return (value or "").strip().lower()


def _validate_password(password: str) -> None:
    if len(password or "") < 8:
        raise ValidationError("Password must be at least 8 characters")


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _check_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _claim_unowned_data(db, user_id: str) -> None:
    models = [
        SubjectMastery,
        TopicMastery,
        StudySession,
        SessionMessage,
        Assessment,
        AssessmentQuestion,
        StudyPlan,
        PlanTask,
        SpacedRepetitionCard,
        ExamBlueprint,
        ExamTopicWeight,
        Document,
        KnowledgeChunk,
        PointLedger,
        Achievement,
        RewardsProfile,
    ]
    for model in models:
        db.query(model).filter(model.user_id.is_(None)).update(
            {"user_id": user_id},
            synchronize_session=False,
        )


@bp.route("/register", methods=["POST"])
def register():
    body = request.get_json(force=True)
    email = _normalize_email(body.get("email", ""))
    password = body.get("password", "")
    display_name = (body.get("display_name", "") or "").strip() or "Law Student"
    claim_existing_data = bool(body.get("claim_existing_data", True))

    if not _EMAIL_RE.match(email):
        raise ValidationError("Valid email is required")
    _validate_password(password)

    with get_db() as db:
        if db.query(User).filter_by(email=email).first():
            raise ValidationError("An account with that email already exists")

        user = User(
            email=email,
            password_hash=_hash_password(password),
            display_name=display_name,
            tier="free",
            subscription_status="none",
        )
        db.add(user)
        db.flush()

        user_count = db.query(User).count()
        if claim_existing_data and user_count == 1:
            _claim_unowned_data(db, user.id)

    # Seed mastery taxonomy for the new user in a separate transaction.
    try:
        seed_subject_taxonomy(user_id=user.id)
    except IntegrityError:
        # Legacy DB may still have old unique indexes.
        pass
    seed_achievements(user_id=user.id)

    return jsonify(
        {
            "user": user.to_dict(),
            **issue_auth_tokens(user.id),
        }
    ), 201


@bp.route("/login", methods=["POST"])
def login():
    body = request.get_json(force=True)
    email = _normalize_email(body.get("email", ""))
    password = body.get("password", "")
    if not email or not password:
        raise ValidationError("email and password are required")

    with get_db() as db:
        user = db.query(User).filter_by(email=email).first()
        if not user or not _check_password(password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")
        try:
            seed_subject_taxonomy(user_id=user.id)
        except IntegrityError:
            pass
        seed_achievements(user_id=user.id)
        payload = {
            "user": user.to_dict(),
            **issue_auth_tokens(user.id),
        }
    return jsonify(payload)


@bp.route("/refresh", methods=["POST"])
def refresh():
    body = request.get_json(force=True)
    refresh_token = (body.get("refresh_token") or "").strip()
    if not refresh_token:
        raise ValidationError("refresh_token is required")

    payload = decode_token(refresh_token, expected_type="refresh")
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid token payload")

    with get_db() as db:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            raise UnauthorizedError("User not found")
        return jsonify(
            {
                "user": user.to_dict(),
                **issue_auth_tokens(user.id),
            }
        )


@bp.route("/me", methods=["GET"])
@login_required
def me():
    user = get_current_user()
    return jsonify(user.to_dict())


@bp.route("/update-profile", methods=["PUT"])
@login_required
def update_profile():
    user_id = get_current_user_id()
    body = request.get_json(force=True)
    display_name = body.get("display_name")
    avatar_url = body.get("avatar_url")

    with get_db() as db:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            raise UnauthorizedError("User not found")
        if display_name is not None:
            display_name = (display_name or "").strip()
            if not display_name:
                raise ValidationError("display_name cannot be empty")
            user.display_name = display_name
        if avatar_url is not None:
            user.avatar_url = (avatar_url or "").strip() or None
        db.flush()
        return jsonify(user.to_dict())


@bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    user_id = get_current_user_id()
    body = request.get_json(force=True)
    current_password = body.get("current_password", "")
    new_password = body.get("new_password", "")
    if not current_password or not new_password:
        raise ValidationError("current_password and new_password are required")
    _validate_password(new_password)

    with get_db() as db:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            raise UnauthorizedError("User not found")
        if not _check_password(current_password, user.password_hash):
            raise UnauthorizedError("Current password is incorrect")
        user.password_hash = _hash_password(new_password)
        db.flush()
        return jsonify({"status": "ok"})
