import hashlib
import os

PLATFORM_ADMIN_USERNAME = "admin"
PLATFORM_ADMIN_PASSWORD = "123456"

SESSION_AUTH = "auth"
SESSION_USERNAME = "username"
SESSION_CLINIC_ID = "clinic_id"
SESSION_CLINIC_NAME = "clinic_name"
SESSION_USER_ID = "user_id"

AUTH_PLATFORM = "platform_admin"
AUTH_CLINIC = "clinic"


def session_secret() -> str:
    return os.environ.get("SESSION_SECRET", "clinic-crm-session-change-in-production")


def hash_password(password: str) -> str:
    return hashlib.sha256((password or "").encode("utf-8")).hexdigest()


def platform_admin_ok(username: str, password: str) -> bool:
    return username.strip().lower() == PLATFORM_ADMIN_USERNAME and password == PLATFORM_ADMIN_PASSWORD


def _session_get(request, key: str, default=None):
    if "session" not in request.scope:
        return default
    return request.session.get(key, default)


def is_platform_admin(request) -> bool:
    return _session_get(request, SESSION_AUTH) == AUTH_PLATFORM


def is_clinic_user(request) -> bool:
    return _session_get(request, SESSION_AUTH) == AUTH_CLINIC


def clinic_id_from_session(request) -> int | None:
    raw = _session_get(request, SESSION_CLINIC_ID)
    if raw is None:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None
