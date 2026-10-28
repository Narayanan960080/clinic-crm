import re
from datetime import date, datetime, timedelta

from app.db import db_conn

STATUS_UI = {
    "active": ("Active", "active"),
    "follow_up": ("Follow-up", "follow-up"),
    "new": ("New", "new"),
    "inactive": ("Inactive", "inactive"),
}

STATUS_FROM_LABEL = {
    "active": "active",
    "follow-up": "follow_up",
    "new": "new",
    "inactive": "inactive",
}

PAYMENT_UI = {
    "paid": ("Paid", "pill-paid"),
    "pending": ("Pending", "pill-pending"),
    "unpaid": ("Unpaid", "pill-unpaid"),
}

AUTO_VISIT_FROM_APPT = "Marked attended from appointment."


def _initials(name: str) -> str:
    parts = [p for p in (name or "").split() if p]
    return "".join(p[0] for p in parts[:2]).upper()


def parse_display_date(text: str) -> date | None:
    text = (text or "").strip()
    m = re.match(r"^(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})$", text)
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def format_display_date(value: date | datetime | None) -> str:
    if not value:
        return ""
    if isinstance(value, datetime):
        value = value.date()
    return f"{value.day:02d} / {value.month:02d} / {value.year}"


def format_time(value: datetime) -> str:
    hour = value.hour
    minute = value.minute
    suffix = "AM" if hour < 12 else "PM"
    hour12 = hour % 12 or 12
    return f"{hour12}:{minute:02d} {suffix}"


def format_time_24(value: datetime) -> str:
    return value.strftime("%H:%M")


def parse_time_text(text: str) -> tuple[int, int] | None:
    text = (text or "").strip()
    m = re.match(r"^(\d{1,2}):(\d{2})\s*(AM|PM)$", text, re.I)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        meridiem = m.group(3).upper()
        if meridiem == "PM" and hour != 12:
            hour += 12
        if meridiem == "AM" and hour == 12:
            hour = 0
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute
        return None
    m = re.match(r"^(\d{1,2}):(\d{2})$", text)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute
    return None


def next_mrn(cur, clinic_id: int) -> str:
    cur.execute(
        "SELECT mrn FROM patients WHERE clinic_id = %s ORDER BY id DESC LIMIT 1",
        (clinic_id,),
    )
    row = cur.fetchone()
    if not row:
        return "MRN-1000"
    digits = re.sub(r"\D", "", row["mrn"] or "")
    num = int(digits) if digits else 999
    return f"MRN-{num + 1}"


def get_or_create_doctor(cur, name: str, department: str = "General", clinic_id: int = 0) -> int:
    name = name.strip()
    cur.execute(
        "SELECT id FROM doctors WHERE clinic_id = %s AND name = %s LIMIT 1",
        (clinic_id, name),
    )
    row = cur.fetchone()
    if row:
        return row["id"]
    cur.execute(
        "INSERT INTO doctors (clinic_id, name, department) VALUES (%s, %s, %s)",
        (clinic_id, name, department),
    )
    return cur.lastrowid


def _latest_payment(cur, patient_id: int) -> tuple[str, str]:
    cur.execute(
        """
        SELECT payment_status FROM appointments
        WHERE patient_id = %s
        ORDER BY start_time DESC LIMIT 1
        """,
        (patient_id,),
    )
    row = cur.fetchone()
    key = (row["payment_status"] if row else "pending") or "pending"
    label, css = PAYMENT_UI.get(key, ("Pending", "pill-pending"))
    return label, css


def _last_visit(cur, patient_id: int) -> tuple[str, str]:
    cur.execute(
        """
        SELECT start_time FROM appointments
        WHERE patient_id = %s AND status = 'completed'
        ORDER BY start_time DESC LIMIT 1
        """,
        (patient_id,),
    )
    row = cur.fetchone()
    if not row:
        return "—", "Not yet"
    dt = row["start_time"]
    return format_display_date(dt), format_time(dt)


def row_to_patient(row, cur) -> dict:
    status_label, status_key = STATUS_UI.get(row["status"], ("New", "new"))
    payment, payment_class = _latest_payment(cur, row["id"])
    last_visit, last_time = _last_visit(cur, row["id"])
    doctor = "—"
    department = row["department"] or "General"
    if row.get("doctor_name"):
        doctor = row["doctor_name"]
    dept_key = (department or "general").lower().replace(" ", "-")
    return {
        "id": row["id"],
        "name": row["full_name"],
        "phone": row["phone"] or "",
        "email": row["email"] or "",
        "dob": format_display_date(row["dob"]),
        "address": row["address"] or "",
        "notes": row["notes"] or "",
        "mrn": row["mrn"],
        "doctor": doctor,
        "department": department,
        "dept_key": dept_key if dept_key != "general" else "general",
        "status": status_label,
        "status_key": status_key,
        "payment": payment,
        "payment_class": payment_class,
        "initials": _initials(row["full_name"]),
        "last_visit": last_visit,
        "last_time": last_time,
        "created_at": row["created_at"].isoformat() if row.get("created_at") else "",
        "clinic_id": row.get("clinic_id") or 0,
    }


def list_patients(q: str = "", clinic_id: int = 0) -> list[dict]:
    q = (q or "").strip()
    sql = """
        SELECT p.*, d.name AS doctor_name
        FROM patients p
        LEFT JOIN doctors d ON d.id = p.doctor_id
        WHERE p.clinic_id = %s
    """
    params: list = [clinic_id]
    if q:
        sql += " AND (p.full_name LIKE %s OR p.phone LIKE %s OR p.mrn LIKE %s)"
        like = f"%{q}%"
        params.extend([like, like, like])
    sql += " ORDER BY p.created_at DESC"
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            return [row_to_patient(r, cur) for r in rows]


def patient_stats(clinic_id: int = 0) -> dict:
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM patients WHERE clinic_id = %s", (clinic_id,))
            total = cur.fetchone()["c"]
            cur.execute(
                """
                SELECT COUNT(*) AS c FROM patients
                WHERE clinic_id = %s
                  AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                """,
                (clinic_id,),
            )
            new_week = cur.fetchone()["c"]
            cur.execute(
                """
                SELECT COUNT(*) AS c FROM appointments a
                JOIN patients p ON p.id = a.patient_id
                WHERE p.clinic_id = %s
                  AND DATE(a.start_time) = CURDATE()
                  AND a.status IN ('pending', 'confirmed')
                """,
                (clinic_id,),
            )
            today_appts = cur.fetchone()["c"]
            cur.execute(
                "SELECT COUNT(*) AS c FROM patients WHERE clinic_id = %s AND status = 'follow_up'",
                (clinic_id,),
            )
            follow_ups = cur.fetchone()["c"]
    return {
        "total": total,
        "new_week": new_week,
        "today_appointments": today_appts,
        "follow_ups": follow_ups,
    }


def create_patient(
    full_name: str,
    dob_text: str,
    phone: str,
    clinic_id: int,
    email: str = "",
    address: str = "",
    notes: str = "",
) -> int:
    from app.validation import validate_patient_fields

    if clinic_id <= 0:
        raise ValueError("Clinic not selected.")
    field_err = validate_patient_fields(full_name, phone, address, email)
    if field_err:
        raise ValueError(field_err)
    dob = parse_display_date(dob_text)
    if not dob:
        raise ValueError("Choose date of birth from the calendar.")
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM patients
                WHERE clinic_id = %s AND full_name = %s AND phone = %s AND dob = %s
                LIMIT 1
                """,
                (clinic_id, full_name.strip(), phone.strip(), dob),
            )
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    """
                    UPDATE patients
                    SET dob = %s, email = %s, address = %s, notes = %s, department = COALESCE(department, 'General')
                    WHERE id = %s AND clinic_id = %s
                    """,
                    (
                        dob,
                        email.strip() or None,
                        address.strip() or None,
                        notes.strip() or None,
                        existing["id"],
                        clinic_id,
                    ),
                )
                return existing["id"]
            mrn = next_mrn(cur, clinic_id)
            cur.execute(
                """
                INSERT INTO patients (clinic_id, mrn, full_name, dob, phone, email, address, notes, status, department)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'new', 'General')
                """,
                (
                    clinic_id,
                    mrn,
                    full_name.strip(),
                    dob,
                    phone.strip(),
                    email.strip() or None,
                    address.strip() or None,
                    notes.strip() or None,
                ),
            )
            return cur.lastrowid


def _patient_row_query(where_sql: str) -> str:
    return f"""
        SELECT p.*, d.name AS doctor_name
        FROM patients p
        LEFT JOIN doctors d ON d.id = p.doctor_id
        WHERE {where_sql}
        LIMIT 1
    """


def find_patient_by_name(name: str, clinic_id: int = 0) -> dict | None:
    name = (name or "").strip()
    if not name or clinic_id <= 0:
        return None
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                _patient_row_query("p.full_name = %s AND p.clinic_id = %s"),
                (name, clinic_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            return patient_detail(row, cur)


def find_patient_by_id(patient_id: int, clinic_id: int = 0) -> dict | None:
    try:
        patient_id = int(patient_id)
    except (TypeError, ValueError):
        return None
    if patient_id <= 0 or clinic_id <= 0:
        return None
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                _patient_row_query("p.id = %s AND p.clinic_id = %s"),
                (patient_id, clinic_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            return patient_detail(row, cur)


def update_patient(
    patient_id: int,
    clinic_id: int,
    full_name: str,
    dob_text: str,
    phone: str,
    email: str = "",
    address: str = "",
    notes: str = "",
    doctor_name: str = "",
    department: str = "General",
    status_label: str = "Active",
) -> None:
    from app.validation import validate_patient_fields

    field_err = validate_patient_fields(full_name, phone, address, email)
    if field_err:
        raise ValueError(field_err)
    dob = parse_display_date(dob_text)
    if not dob:
        raise ValueError("Choose date of birth from the calendar.")
    if clinic_id <= 0:
        raise ValueError("Clinic not selected.")
    status_key = STATUS_FROM_LABEL.get((status_label or "").strip().lower(), "active")
    dept = (department or "General").strip() or "General"
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM patients WHERE id = %s AND clinic_id = %s LIMIT 1",
                (patient_id, clinic_id),
            )
            if not cur.fetchone():
                raise ValueError("Patient not found.")
            doctor_id = None
            if doctor_name.strip():
                doctor_id = get_or_create_doctor(cur, doctor_name.strip(), dept, clinic_id)
            cur.execute(
                """
                UPDATE patients
                SET full_name = %s,
                    dob = %s,
                    phone = %s,
                    email = %s,
                    address = %s,
                    notes = %s,
                    doctor_id = %s,
                    department = %s,
                    status = %s
                WHERE id = %s AND clinic_id = %s
                """,
                (
                    full_name.strip(),
                    dob,
                    phone.strip(),
                    email.strip() or None,
                    address.strip() or None,
                    notes.strip() or None,
                    doctor_id,
                    dept,
                    status_key,
                    patient_id,
                    clinic_id,
                ),
            )


def patient_detail(row, cur) -> dict:
    base = row_to_patient(row, cur)
    pid = row["id"]

    cur.execute(
        """
        SELECT a.*, d.name AS doctor_name
        FROM appointments a
        JOIN doctors d ON d.id = a.doctor_id
        WHERE a.patient_id = %s AND a.status = 'completed'
        ORDER BY a.start_time DESC
        """,
        (pid,),
    )
    appt_rows = cur.fetchall()
    visited = []
    history_events = []
    for appt in appt_rows:
        pay_label, pay_class = PAYMENT_UI.get(appt["payment_status"], ("Pending", "pill-pending"))
        visited.append(
            {
                "date": format_display_date(appt["start_time"]),
                "time": format_time(appt["start_time"]),
                "doctor": appt["doctor_name"],
                "reason": appt["reason"],
                "payment": pay_label,
                "payment_class": pay_class,
            }
        )
        start = appt["start_time"]
        history_events.append(
            {
                "kind": "appointment",
                "kind_label": "Appointment",
                "sort": start,
                "date": format_display_date(start),
                "time": format_time(start),
                "when_label": f"{format_display_date(start)} · {format_time(start)}",
                "title": appt["reason"] or "Appointment",
                "subtitle": appt["doctor_name"],
                "notes": "",
                "payment": pay_label,
                "payment_class": pay_class,
            }
        )

    cur.execute(
        """
        SELECT v.visit_date, v.title, v.notes, d.name AS doctor_name
        FROM visits v
        LEFT JOIN doctors d ON d.id = v.doctor_id
        WHERE v.patient_id = %s
        ORDER BY v.visit_date DESC
        """,
        (pid,),
    )
    timeline = []
    for v in cur.fetchall():
        notes = (v["notes"] or "").strip()
        timeline.append((format_display_date(v["visit_date"]), v["title"], notes))
        if notes == AUTO_VISIT_FROM_APPT:
            continue
        when = v["visit_date"]
        if isinstance(when, date) and not isinstance(when, datetime):
            when = datetime(when.year, when.month, when.day, 9, 0)
        subtitle = v["doctor_name"] or ""
        history_events.append(
            {
                "kind": "visit",
                "kind_label": "Visit",
                "sort": when,
                "date": format_display_date(when),
                "time": "",
                "when_label": format_display_date(when),
                "title": v["title"] or "Visit note",
                "subtitle": subtitle,
                "notes": notes,
                "payment": "",
                "payment_class": "",
            }
        )

    history_events.sort(key=lambda item: item["sort"], reverse=True)

    cur.execute(
        """
        SELECT a.*, d.name AS doctor_name
        FROM appointments a
        JOIN doctors d ON d.id = a.doctor_id
        WHERE a.patient_id = %s
          AND a.start_time >= NOW()
          AND a.status IN ('pending', 'confirmed')
        ORDER BY a.start_time ASC
        LIMIT 1
        """,
        (pid,),
    )
    nxt = cur.fetchone()
    next_block = None
    if nxt:
        pay_label, pay_class = PAYMENT_UI.get(nxt["payment_status"], ("Pending", "pill-pending"))
        next_block = {
            "when": f"{format_display_date(nxt['start_time'])} · {format_time(nxt['start_time'])}",
            "detail": nxt["doctor_name"],
            "problem": nxt["reason"],
            "payment": pay_label,
            "payment_class": pay_class,
        }

    base["visited"] = visited
    base["timeline"] = timeline
    base["history_events"] = history_events
    base["next"] = next_block
    base["prescriptions"] = _list_prescriptions(cur, pid)
    base["documents"] = _list_documents(cur, pid)
    if history_events:
        base["last_visit"] = history_events[0]["date"]
    elif visited:
        base["last_visit"] = visited[0]["date"]
    return base


def empty_patient(name: str) -> dict:
    label = (name or "").strip() or "No patient selected"
    return {
        "id": 0,
        "initials": _initials(label) if label != "No patient selected" else "",
        "name": label,
        "phone": "",
        "mrn": "",
        "doctor": "",
        "department": "",
        "payment": "",
        "payment_class": "",
        "dob": "",
        "email": "",
        "address": "",
        "notes": "",
        "next": None,
        "visited": [],
        "timeline": [],
        "history_events": [],
        "prescriptions": [],
        "documents": [],
        "last_visit": "—",
        "status": "",
        "status_key": "",
    }


def _appointment_item(row) -> dict:
    pay_label, pay_class = PAYMENT_UI.get(row["payment_status"], ("Pending", "pill-pending"))
    status = row["status"]
    visit_status = "Confirmed"
    visit_class = ""
    if status == "cancelled":
        visit_status = "Cancelled"
        visit_class = "pill-inactive"
    elif status == "completed":
        visit_status = "Attended"
    return {
        "id": row["id"],
        "patient": row["patient_name"],
        "time": format_time(row["start_time"]),
        "time_24": format_time_24(row["start_time"]),
        "doctor": row["doctor_name"],
        "reason": row["reason"],
        "payment": pay_label,
        "payment_class": pay_class,
        "date": format_display_date(row["start_time"]),
        "date_iso": row["start_time"].strftime("%Y-%m-%d"),
        "status": status,
        "visit_status": visit_status,
        "visit_class": visit_class,
    }


def list_appointments_range(start: date, end: date, clinic_id: int = 0) -> list[dict]:
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT a.*, p.full_name AS patient_name, d.name AS doctor_name
                FROM appointments a
                JOIN patients p ON p.id = a.patient_id
                JOIN doctors d ON d.id = a.doctor_id
                WHERE p.clinic_id = %s
                  AND DATE(a.start_time) BETWEEN %s AND %s
                  AND a.status IN ('pending', 'confirmed', 'completed', 'cancelled')
                ORDER BY a.start_time ASC
                """,
                (clinic_id, start, end),
            )
            return [_appointment_item(r) for r in cur.fetchall()]


def current_week_bounds() -> tuple[date, date]:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def list_week_appointments(clinic_id: int = 0) -> list[dict]:
    monday, sunday = current_week_bounds()
    items = list_appointments_range(monday, sunday, clinic_id)
    return [item for item in items if item.get("status") in ("pending", "confirmed")]


def list_today_appointments(clinic_id: int = 0) -> list[dict]:
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT a.*, p.full_name AS patient_name, d.name AS doctor_name
                FROM appointments a
                JOIN patients p ON p.id = a.patient_id
                JOIN doctors d ON d.id = a.doctor_id
                WHERE p.clinic_id = %s
                  AND DATE(a.start_time) = CURDATE()
                  AND a.status IN ('pending', 'confirmed', 'completed', 'cancelled')
                ORDER BY a.start_time ASC
                """,
                (clinic_id,),
            )
            return [_appointment_item(r) for r in cur.fetchall()]


def week_board(clinic_id: int = 0) -> tuple[list[str], list[list[dict]]]:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    day_names = []
    columns: list[list[dict]] = []
    with db_conn() as conn:
        with conn.cursor() as cur:
            for offset in range(6):
                day = monday + timedelta(days=offset)
                day_names.append(day.strftime("%A %d %b"))
                cur.execute(
                    """
                    SELECT a.*, p.full_name AS patient_name, d.name AS doctor_name
                    FROM appointments a
                    JOIN patients p ON p.id = a.patient_id
                    JOIN doctors d ON d.id = a.doctor_id
                    WHERE p.clinic_id = %s
                      AND DATE(a.start_time) = %s
                      AND a.status IN ('pending', 'confirmed')
                    ORDER BY a.start_time ASC
                    """,
                    (clinic_id, day),
                )
                columns.append([_appointment_item(r) for r in cur.fetchall()])
    return day_names, columns


def book_appointment(
    patient_name: str,
    date_text: str,
    time_text: str,
    doctor_name: str,
    reason: str,
    payment: str,
    clinic_id: int = 0,
) -> int:
    day = parse_display_date(date_text)
    if not day:
        raise ValueError("Invalid date.")
    parsed = parse_time_text(time_text)
    if not parsed:
        raise ValueError("Invalid time.")
    start = datetime(day.year, day.month, day.day, parsed[0], parsed[1])
    end = start + timedelta(minutes=15)
    pay_key = payment.strip().lower()
    if pay_key not in PAYMENT_UI:
        pay_key = "pending"

    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM patients WHERE full_name = %s AND clinic_id = %s LIMIT 1",
                (patient_name.strip(), clinic_id),
            )
            prow = cur.fetchone()
            if not prow:
                raise ValueError("Patient not found. Register them under Patients first.")
            doctor_id = get_or_create_doctor(cur, doctor_name, "General", clinic_id)
            try:
                cur.execute(
                    """
                    INSERT INTO appointments
                      (patient_id, doctor_id, start_time, end_time, reason, status, payment_status)
                    VALUES (%s, %s, %s, %s, %s, 'confirmed', %s)
                    """,
                    (prow["id"], doctor_id, start, end, reason.strip(), pay_key),
                )
            except Exception as exc:
                msg = str(exc).lower()
                if "time slot" in msg or "45000" in msg:
                    raise ValueError("That doctor already has an appointment at that time.") from exc
                raise
            return cur.lastrowid


def set_appointment_status(appointment_id: int, action: str, clinic_id: int = 0) -> None:
    if action == "cancel":
        status = "cancelled"
    elif action == "attended":
        status = "completed"
    else:
        raise ValueError("Unknown action.")
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT a.patient_id, a.start_time, a.reason, a.doctor_id
                FROM appointments a
                JOIN patients p ON p.id = a.patient_id
                WHERE a.id = %s AND p.clinic_id = %s
                """,
                (appointment_id, clinic_id),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("Appointment not found.")
            cur.execute("UPDATE appointments SET status = %s WHERE id = %s", (status, appointment_id))
            if status == "completed":
                cur.execute(
                    """
                    INSERT INTO visits (patient_id, doctor_id, visit_date, title, notes)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        row["patient_id"],
                        row["doctor_id"],
                        row["start_time"],
                        row["reason"] or "Visit",
                        AUTO_VISIT_FROM_APPT,
                    ),
                )


def add_visit_note(patient_name: str, title: str, date_text: str, notes: str, clinic_id: int = 0) -> None:
    when = parse_display_date(date_text)
    if not when:
        raise ValueError("Enter date as DD / MM / YYYY.")
    visit_dt = datetime(when.year, when.month, when.day, 9, 0)
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM patients WHERE full_name = %s AND clinic_id = %s LIMIT 1",
                (patient_name.strip(), clinic_id),
            )
            prow = cur.fetchone()
            if not prow:
                raise ValueError("Patient not found.")
            cur.execute(
                """
                INSERT INTO visits (patient_id, doctor_id, visit_date, title, notes)
                VALUES (%s, NULL, %s, %s, %s)
                """,
                (prow["id"], visit_dt, title.strip(), notes.strip()),
            )


def _list_prescriptions(cur, patient_id: int) -> list[dict]:
    cur.execute(
        """
        SELECT id, prescribed_on, medication, dosage, instructions, created_at
        FROM prescriptions
        WHERE patient_id = %s
        ORDER BY prescribed_on DESC, id DESC
        """,
        (patient_id,),
    )
    items = []
    for row in cur.fetchall():
        items.append(
            {
                "id": row["id"],
                "date": format_display_date(row["prescribed_on"]),
                "medication": row["medication"],
                "dosage": row["dosage"],
                "instructions": row["instructions"] or "",
            }
        )
    return items


def add_prescription(
    patient_name: str,
    date_text: str,
    medication: str,
    dosage: str,
    instructions: str = "",
    clinic_id: int = 0,
) -> None:
    when = parse_display_date(date_text)
    if not when:
        raise ValueError("Choose prescription date from the calendar.")
    med = medication.strip()
    dose = dosage.strip()
    if len(med) < 2:
        raise ValueError("Enter medication name.")
    if len(dose) < 1:
        raise ValueError("Enter dosage.")
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM patients WHERE full_name = %s AND clinic_id = %s LIMIT 1",
                (patient_name.strip(), clinic_id),
            )
            prow = cur.fetchone()
            if not prow:
                raise ValueError("Patient not found.")
            cur.execute(
                """
                INSERT INTO prescriptions (patient_id, prescribed_on, medication, dosage, instructions)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (prow["id"], when, med, dose, instructions.strip() or None),
            )


def _list_documents(cur, patient_id: int) -> list[dict]:
    cur.execute(
        """
        SELECT id, original_name, label, content_type, size_bytes, uploaded_at
        FROM patient_documents
        WHERE patient_id = %s
        ORDER BY uploaded_at DESC, id DESC
        """,
        (patient_id,),
    )
    items = []
    for row in cur.fetchall():
        size_kb = max(1, int(round(row["size_bytes"] / 1024)))
        items.append(
            {
                "id": row["id"],
                "name": row["original_name"],
                "label": row["label"] or row["original_name"],
                "content_type": row["content_type"],
                "size_kb": size_kb,
                "uploaded": format_display_date(row["uploaded_at"]),
            }
        )
    return items


def insert_patient_document(
    patient_id: int,
    original_name: str,
    stored_name: str,
    content_type: str,
    size_bytes: int,
    label: str = "",
) -> int:
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM patients WHERE id = %s LIMIT 1", (patient_id,))
            if not cur.fetchone():
                raise ValueError("Patient not found.")
            cur.execute(
                """
                INSERT INTO patient_documents
                  (patient_id, original_name, stored_name, content_type, size_bytes, label)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    patient_id,
                    original_name,
                    stored_name,
                    content_type or "application/octet-stream",
                    size_bytes,
                    label.strip() or None,
                ),
            )
            return cur.lastrowid


def get_patient_document(doc_id: int, clinic_id: int = 0) -> dict | None:
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT d.id, d.patient_id, d.original_name, d.stored_name, d.content_type, d.size_bytes
                FROM patient_documents d
                JOIN patients p ON p.id = d.patient_id
                WHERE d.id = %s AND p.clinic_id = %s
                LIMIT 1
                """,
                (doc_id, clinic_id),
            )
            return cur.fetchone()
