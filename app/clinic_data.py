PATIENTS = []
BY_NAME = {}
WEEK = [[], [], [], [], [], []]
TODAY = []


def patient_by_name(name: str) -> dict:
    found = BY_NAME.get((name or "").strip())
    if found:
        return found
    label = (name or "").strip() or "No patient selected"
    initials = ""
    if label != "No patient selected":
        initials = "".join(part[0] for part in label.split()[:2]).upper()
    return {
        "initials": initials,
        "name": label,
        "phone": "",
        "mrn": "",
        "doctor": "",
        "department": "",
        "payment": "",
        "payment_class": "",
        "dob": "",
        "email": "",
        "notes": "",
        "next": None,
        "visited": [],
        "timeline": [],
    }
