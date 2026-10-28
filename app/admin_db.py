from app.auth import hash_password
from app.db import db_conn

DEFAULT_CLINIC_NAME = "Quantamloop Demo Clinic"
LEGACY_DEMO_USERNAMES = frozenset({"lakhmi", "dr.name@clinic.com"})

# Seeded on startup if missing (shown in admin “Clinic users”).
BUILTIN_CLINIC_USERS = (
    {"username": "lakshmi", "name": "Lakshmi", "password": "123456", "phone": "9845010000"},
)


def ensure_clinic_named(name: str) -> dict:
    name = (name or DEFAULT_CLINIC_NAME).strip()
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, is_active FROM clinics WHERE name = %s LIMIT 1",
                (name,),
            )
            row = cur.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "is_active": bool(row.get("is_active", 1)),
                }
            cur.execute(
                "INSERT INTO clinics (name, phone, address) VALUES (%s, NULL, NULL)",
                (name,),
            )
            return {"id": cur.lastrowid, "name": name, "is_active": True}


def ensure_default_clinic() -> int:
    return ensure_clinic_named(DEFAULT_CLINIC_NAME)["id"]


def legacy_demo_clinic() -> dict:
    return ensure_clinic_named(DEFAULT_CLINIC_NAME)


def ensure_builtin_clinic_users() -> None:
    clinic = ensure_clinic_named(DEFAULT_CLINIC_NAME)
    clinic_id = clinic["id"]
    with db_conn() as conn:
        with conn.cursor() as cur:
            for spec in BUILTIN_CLINIC_USERS:
                username = spec["username"].strip()
                demo_phone = (spec.get("phone") or "").strip()
                cur.execute(
                    "SELECT id, phone FROM clinic_users WHERE username = %s LIMIT 1",
                    (username,),
                )
                existing = cur.fetchone()
                if existing:
                    if demo_phone and not (existing.get("phone") or "").strip():
                        cur.execute(
                            "UPDATE clinic_users SET phone = %s WHERE id = %s",
                            (demo_phone, existing["id"]),
                        )
                    continue
                cur.execute(
                    """
                    INSERT INTO clinic_users (clinic_id, name, username, email, phone, password_hash, role)
                    VALUES (%s, %s, %s, '', %s, %s, 'admin')
                    """,
                    (
                        clinic_id,
                        spec["name"].strip(),
                        username,
                        demo_phone,
                        hash_password(spec["password"]),
                    ),
                )


def clinic_phone_taken(phone: str, exclude_clinic_id: int = 0) -> bool:
    from app.validation import normalize_phone_digits

    digits = normalize_phone_digits(phone)
    if not digits:
        return False
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, phone FROM clinics WHERE phone IS NOT NULL AND phone != ''")
            for row in cur.fetchall():
                if row["id"] == exclude_clinic_id:
                    continue
                if normalize_phone_digits(row["phone"]) == digits:
                    return True
    return False


def list_clinics() -> list[dict]:
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id, c.name, c.phone, c.address, c.created_at, c.is_active,
                       (SELECT COUNT(*) FROM clinic_users u WHERE u.clinic_id = c.id) AS user_count,
                       (SELECT COUNT(*) FROM patients p WHERE p.clinic_id = c.id) AS patient_count
                FROM clinics c
                ORDER BY c.name ASC
                """
            )
            rows = cur.fetchall()
            return [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "phone": row["phone"] or "",
                    "address": row["address"] or "",
                    "user_count": row["user_count"],
                    "patient_count": row.get("patient_count") or 0,
                    "is_active": bool(row.get("is_active", 1)),
                }
                for row in rows
            ]


def create_clinic(name: str, phone: str = "", address: str = "") -> int:
    from app.validation import validate_clinic_fields

    name = name.strip()
    err = validate_clinic_fields(name, phone, address)
    if err:
        raise ValueError(err)
    if clinic_phone_taken(phone):
        raise ValueError("A clinic with this mobile number already exists.")
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM clinics WHERE name = %s LIMIT 1", (name,))
            if cur.fetchone():
                raise ValueError("A clinic with this name already exists.")
            cur.execute(
                "INSERT INTO clinics (name, phone, address) VALUES (%s, %s, %s)",
                (name, phone.strip() or None, address.strip() or None),
            )
            return cur.lastrowid


def list_clinic_users() -> list[dict]:
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.id, u.clinic_id, u.name, u.username, u.email, u.phone, u.role,
                       u.is_active, c.name AS clinic_name, c.is_active AS clinic_is_active
                FROM clinic_users u
                JOIN clinics c ON c.id = u.clinic_id
                ORDER BY c.name ASC, u.username ASC
                """
            )
            return [
                {
                    "id": row["id"],
                    "clinic_id": row["clinic_id"],
                    "name": row["name"],
                    "username": row["username"],
                    "email": row["email"] or "",
                    "phone": row["phone"] or "",
                    "role": row["role"],
                    "clinic_name": row["clinic_name"],
                    "is_active": bool(row.get("is_active", 1)),
                    "clinic_is_active": bool(row.get("clinic_is_active", 1)),
                }
                for row in cur.fetchall()
            ]


def set_clinic_active(clinic_id: int, active: bool) -> None:
    if clinic_id <= 0:
        raise ValueError("Invalid clinic.")
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM clinics WHERE id = %s LIMIT 1", (clinic_id,))
            if not cur.fetchone():
                raise ValueError("Clinic not found.")
            cur.execute(
                "UPDATE clinics SET is_active = %s WHERE id = %s",
                (1 if active else 0, clinic_id),
            )


def set_clinic_user_active(user_id: int, active: bool) -> None:
    if user_id <= 0:
        raise ValueError("Invalid user.")
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM clinic_users WHERE id = %s LIMIT 1", (user_id,))
            if not cur.fetchone():
                raise ValueError("User not found.")
            cur.execute(
                "UPDATE clinic_users SET is_active = %s WHERE id = %s",
                (1 if active else 0, user_id),
            )


def platform_overview() -> dict:
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM clinics")
            clinics_total = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM clinics WHERE is_active = 1")
            clinics_active = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM clinic_users")
            users_total = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM clinic_users WHERE is_active = 1")
            users_active = cur.fetchone()["c"]
            cur.execute("SHOW TABLES LIKE 'patients'")
            has_patients = cur.fetchone()
            if has_patients:
                cur.execute("SELECT COUNT(*) AS c FROM patients")
                patients_total = cur.fetchone()["c"]
            else:
                patients_total = 0
            if has_patients:
                cur.execute(
                    """
                    SELECT c.name, COUNT(p.id) AS patient_count
                    FROM clinics c
                    LEFT JOIN patients p ON p.clinic_id = c.id
                    GROUP BY c.id, c.name
                    ORDER BY patient_count DESC, c.name ASC
                    LIMIT 8
                    """
                )
                rows = cur.fetchall()
            else:
                cur.execute(
                    "SELECT name, 0 AS patient_count FROM clinics ORDER BY name ASC LIMIT 8"
                )
                rows = cur.fetchall()
    counts = [int(row["patient_count"] or 0) for row in rows]
    peak = max(counts) if counts else 0
    chart = []
    for row in rows:
        count = int(row["patient_count"] or 0)
        pct = round((count / peak) * 100) if peak else 0
        chart.append({"label": row["name"], "count": count, "pct": pct})
    return {
        "clinics_total": clinics_total,
        "clinics_active": clinics_active,
        "users_total": users_total,
        "users_active": users_active,
        "patients_total": patients_total,
        "chart": chart,
    }


def clinic_user_phone_taken(phone: str, exclude_user_id: int = 0) -> bool:
    from app.validation import normalize_phone_digits

    digits = normalize_phone_digits(phone)
    if not digits:
        return False
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, phone FROM clinic_users WHERE phone IS NOT NULL AND phone != ''")
            for row in cur.fetchall():
                if row["id"] == exclude_user_id:
                    continue
                if normalize_phone_digits(row["phone"]) == digits:
                    return True
    return False


def create_clinic_user(
    clinic_id: int,
    name: str,
    username: str,
    password: str,
    email: str = "",
    phone: str = "",
) -> int:
    name = name.strip()
    username = username.strip()
    if clinic_id <= 0:
        raise ValueError("Choose a clinic.")
    from app.validation import validate_clinic_user_fields

    from app.validation import validate_username

    err = validate_clinic_user_fields(name, phone, email)
    if err:
        raise ValueError(err)
    err = validate_username(username)
    if err:
        raise ValueError(err)
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    from app.validation import normalize_phone_digits

    phone_digits = normalize_phone_digits(phone)
    if clinic_user_phone_taken(phone_digits):
        raise ValueError("That mobile number is already registered to a clinic user.")
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM clinics WHERE id = %s LIMIT 1", (clinic_id,))
            if not cur.fetchone():
                raise ValueError("Clinic not found.")
            cur.execute("SELECT id FROM clinic_users WHERE username = %s LIMIT 1", (username,))
            if cur.fetchone():
                raise ValueError("That username is already in use.")
            cur.execute(
                """
                INSERT INTO clinic_users (clinic_id, name, username, email, phone, password_hash, role)
                VALUES (%s, %s, %s, %s, %s, %s, 'admin')
                """,
                (
                    clinic_id,
                    name,
                    username,
                    email.strip() or "",
                    phone_digits,
                    hash_password(password),
                ),
            )
            return cur.lastrowid


def _clinic_user_session(row: dict) -> dict:
    return {
        "id": row["id"],
        "clinic_id": row["clinic_id"],
        "username": row["username"],
        "name": row["name"],
        "clinic_name": row["clinic_name"],
    }


def _login_active_error(row: dict) -> str | None:
    if not bool(row.get("is_active", 1)):
        return "inactive_user"
    if not bool(row.get("clinic_is_active", 1)):
        return "inactive_clinic"
    return None


def verify_clinic_login(username: str, password: str) -> tuple[dict | None, str | None]:
    """Return (session_user, error_code). error_code: inactive_user | inactive_clinic."""
    from app.validation import normalize_phone_digits

    identifier = (username or "").strip()
    if not identifier:
        return None, None
    digest = hash_password(password)
    user_cols = """
                u.id, u.clinic_id, u.username, u.name, u.phone, u.is_active,
                c.name AS clinic_name, c.is_active AS clinic_is_active
    """
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {user_cols}
                FROM clinic_users u
                JOIN clinics c ON c.id = u.clinic_id
                WHERE u.username = %s AND u.password_hash = %s
                LIMIT 1
                """,
                (identifier, digest),
            )
            row = cur.fetchone()
            if row:
                blocked = _login_active_error(row)
                if blocked:
                    return None, blocked
                return _clinic_user_session(row), None
            digits = normalize_phone_digits(identifier)
            if len(digits) != 10:
                return None, None
            cur.execute(
                f"""
                SELECT {user_cols}
                FROM clinic_users u
                JOIN clinics c ON c.id = u.clinic_id
                WHERE u.password_hash = %s
                """,
                (digest,),
            )
            for row in cur.fetchall():
                if normalize_phone_digits(row.get("phone") or "") == digits:
                    blocked = _login_active_error(row)
                    if blocked:
                        return None, blocked
                    return _clinic_user_session(row), None
    return None, None


def legacy_clinic_login_ok(username: str, password: str) -> tuple[bool, str | None]:
    name = username.strip().lower()
    if name not in LEGACY_DEMO_USERNAMES or password != "123456":
        return False, None
    clinic = legacy_demo_clinic()
    if not clinic.get("is_active", True):
        return False, "inactive_clinic"
    return True, None
