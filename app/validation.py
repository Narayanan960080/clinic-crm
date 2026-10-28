import re


def _letters(text: str) -> int:
    return sum(1 for c in text if c.isalpha())


def validate_name(name: str, label: str = "Name") -> str | None:
    text = (name or "").strip()
    if len(text) < 3 or _letters(text) < 3:
        return f"{label} must be at least 3 letters."
    return None


def validate_phone(phone: str, required: bool = True) -> str | None:
    digits = re.sub(r"\D", "", phone or "")
    if not digits:
        if required:
            return "Enter a 10-digit mobile number."
        return None
    if len(digits) != 10:
        return "Enter a 10-digit mobile number."
    return None


def validate_address(address: str, required: bool = True) -> str | None:
    text = (address or "").strip()
    if not text:
        if required:
            return "Address must be at least 5 characters."
        return None
    if len(text) < 5:
        return "Address must be at least 5 characters."
    return None


def validate_email_optional(email: str) -> str | None:
    text = (email or "").strip()
    if not text:
        return None
    if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", text):
        return "Enter a valid email address, or leave it blank."
    return None


def validate_patient_fields(full_name: str, phone: str, address: str, email: str = "") -> str | None:
    for check in (
        validate_name(full_name, "Full name"),
        validate_phone(phone, True),
        validate_address(address, True),
        validate_email_optional(email),
    ):
        if check:
            return check
    return None


def validate_clinic_fields(name: str, phone: str, address: str) -> str | None:
    err = validate_name(name, "Clinic name")
    if err:
        return err
    err = validate_phone(phone, False)
    if err:
        return err
    return validate_address(address, False)


def validate_clinic_user_fields(name: str, phone: str, email: str) -> str | None:
    err = validate_name(name, "Full name")
    if err:
        return err
    err = validate_phone(phone, True)
    if err:
        return err
    return validate_email_optional(email)


def normalize_phone_digits(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")


def validate_username(username: str) -> str | None:
    text = (username or "").strip()
    if len(text) < 3:
        return "Username must be at least 3 characters."
    if len(text) > 32:
        return "Username must be 32 characters or fewer."
    if not re.match(r"^[a-zA-Z0-9._-]+$", text):
        return "Username may use letters, numbers, dots, underscores and hyphens only."
    return None
