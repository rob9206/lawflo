"""JWT authentication middleware and helpers."""

from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import g, has_request_context, request

from api.config import config
from api.errors import UnauthorizedError
from api.models.user import User
from api.services.database import get_db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _extract_bearer_token() -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise UnauthorizedError("Missing Bearer token")
    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise UnauthorizedError("Missing Bearer token")
    return token


def create_token(user_id: str, token_type: str = "access") -> str:
    if token_type == "refresh":
        exp = _utcnow() + timedelta(days=config.JWT_REFRESH_EXPIRES_DAYS)
    else:
        exp = _utcnow() + timedelta(minutes=config.JWT_ACCESS_EXPIRES_MINUTES)

    payload = {
        "sub": user_id,
        "type": token_type,
        "iat": int(_utcnow().timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, config.JWT_SECRET_KEY, algorithm="HS256")


def decode_token(token: str, expected_type: str = "access") -> dict:
    try:
        payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Invalid token") from exc

    token_type = payload.get("type")
    if expected_type and token_type != expected_type:
        raise UnauthorizedError("Invalid token type")
    return payload


def issue_auth_tokens(user_id: str) -> dict:
    return {
        "access_token": create_token(user_id, "access"),
        "refresh_token": create_token(user_id, "refresh"),
        "token_type": "Bearer",
        "expires_in_seconds": config.JWT_ACCESS_EXPIRES_MINUTES * 60,
    }


def get_current_user(optional: bool = False) -> User | None:
    if not has_request_context():
        if optional:
            return None
        raise UnauthorizedError("Authentication required")
    user = getattr(g, "current_user", None)
    if user is None and not optional:
        raise UnauthorizedError("Authentication required")
    return user


def get_current_user_id(optional: bool = False) -> str | None:
    if not has_request_context():
        if optional:
            return None
        raise UnauthorizedError("Authentication required")
    user_id = getattr(g, "current_user_id", None)
    if not user_id and not optional:
        raise UnauthorizedError("Authentication required")
    return user_id


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_bearer_token()
        payload = decode_token(token, expected_type="access")
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedError("Invalid token payload")

        with get_db() as db:
            user = db.query(User).filter_by(id=user_id).first()
            if not user:
                raise UnauthorizedError("User not found")
            g.current_user = user
            g.current_user_id = user.id

        return fn(*args, **kwargs)

    return wrapper
