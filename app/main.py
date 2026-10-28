import json
import uuid
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qs, quote

from fastapi import FastAPI, File, Form, Request, UploadFile

import app.admin_db as admin_db
import app.clinic_db as clinic_db
from app.auth import (
    AUTH_CLINIC,
    AUTH_PLATFORM,
    SESSION_AUTH,
    SESSION_CLINIC_ID,
    SESSION_CLINIC_NAME,
    SESSION_USER_ID,
    SESSION_USERNAME,
    clinic_id_from_session,
    is_clinic_user,
    is_platform_admin,
    platform_admin_ok,
    session_secret,
)
from app.db import db_ping
from app.db_schema import ensure_schema
from app.validation import (
    validate_clinic_fields,
    validate_clinic_user_fields,
    validate_patient_fields,
    validate_username,
)
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

BASE = Path(__file__).resolve().parent
UPLOAD_ROOT = BASE / "uploads" / "patients"
ALLOWED_DOC_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".doc", ".docx"}
MAX_DOC_BYTES = 5 * 1024 * 1024


@asynccontextmanager
async def lifespan(_app: FastAPI):
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    if db_ping():
        ensure_schema()
    yield


app = FastAPI(title="Clinic CRM", docs_url=None, redoc_url=None, lifespan=lifespan)

CLINIC_APP_PATHS = ("/dashboard", "/patients", "/appointments", "/history", "/account", "/support")


def resolve_clinic_id(request: Request) -> int:
    clinic_id = clinic_id_from_session(request)
    if clinic_id and clinic_id > 0:
        return clinic_id
    if db_ping():
        clinic_id = admin_db.ensure_default_clinic()
        request.session[SESSION_CLINIC_ID] = clinic_id
        if not request.session.get(SESSION_CLINIC_NAME):
            request.session[SESSION_CLINIC_NAME] = admin_db.DEFAULT_CLINIC_NAME
        return clinic_id
    return 0


@app.middleware("http")
async def clinic_auth_middleware(request: Request, call_next):
    path = request.url.path
    if path.startswith("/static") or path in {"/", "/login", "/logout", "/privacy", "/terms"}:
        return await call_next(request)
    if path.startswith("/admin") or path in {"/robots.txt", "/sitemap.xml"}:
        return await call_next(request)
    if any(path == prefix or path.startswith(prefix + "/") for prefix in CLINIC_APP_PATHS):
        if not is_clinic_user(request):
            return RedirectResponse("/login?error=1", status_code=303)
        resolve_clinic_id(request)
    return await call_next(request)


# SessionMiddleware must wrap auth middleware so request.session is available in clinic_auth_middleware.
app.add_middleware(SessionMiddleware, secret_key=session_secret(), max_age=60 * 60 * 24 * 7)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")

NOTICES = {"1": "Patient saved."}
APPOINTMENT_NOTICE = "Appointment booked."
LOGIN_ERROR = "That mobile, username or password does not match."
LOGIN_INACTIVE_USER = "This account is inactive. Contact your platform admin."
LOGIN_INACTIVE_CLINIC = "This clinic is inactive. Contact platform support."

LOGIN_ERRORS = {
    "1": LOGIN_ERROR,
    "inactive_user": LOGIN_INACTIVE_USER,
    "inactive_clinic": LOGIN_INACTIVE_CLINIC,
}


def load_context(request: Request, q: str = "") -> dict:
    clinic_id = resolve_clinic_id(request) if is_clinic_user(request) else 0
    patients = clinic_db.list_patients(q, clinic_id) if db_ping() and clinic_id else []
    stats = (
        clinic_db.patient_stats(clinic_id)
        if db_ping() and clinic_id
        else {"total": 0, "new_week": 0, "today_appointments": 0, "follow_ups": 0}
    )
    return {
        "request": request,
        "base_url": str(request.base_url).rstrip("/"),
        "json_ld": json_ld(str(request.base_url).rstrip("/")),
        "patients": patients,
        "patients_json": json.dumps(patients).replace("<", "\\u003c"),
        "stats": stats,
        "q": q,
        "clinic_name": request.session.get(SESSION_CLINIC_NAME, ""),
        "session_username": request.session.get(SESSION_USERNAME, ""),
    }


def render(request: Request, name: str, status_code: int = 200, **extra):
    q = extra.get("q", "")
    context = load_context(request, q=q)
    context.update(extra)
    return templates.TemplateResponse(request, name, context, status_code=status_code)


def admin_render(request: Request, name: str, status_code: int = 200, **extra):
    if name == "admin/index.html" and "overview" not in extra:
        extra["overview"] = {}
        if db_ping():
            try:
                extra["overview"] = admin_db.platform_overview()
            except Exception:
                pass
    context = {"request": request, **extra}
    return templates.TemplateResponse(request, name, context, status_code=status_code)


def require_platform_admin(request: Request) -> RedirectResponse | None:
    if not is_platform_admin(request):
        return RedirectResponse("/login?error=1", status_code=303)
    return None


def json_ld(base: str) -> str:
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "name": "Quantamloop Innovation Private Limited",
                "url": base + "/",
            },
            {
                "@type": "SoftwareApplication",
                "name": "Clinic CRM",
                "applicationCategory": "BusinessApplication",
                "operatingSystem": "Web",
                "description": "Patient management software for small clinics, with appointment scheduling and patient records.",
                "provider": {"@type": "Organization", "name": "Quantamloop Innovation Private Limited"},
            },
        ],
    }
    return json.dumps(data).replace("<", "\\u003c")


async def form_body(request: Request) -> dict[str, str]:
    raw = parse_qs((await request.body()).decode())
    return {key: values[0] if values else "" for key, values in raw.items()}


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return render(request, "marketing.html")


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = ""):
    return render(request, "login.html", login_error=LOGIN_ERRORS.get(error, ""))


@app.post("/login")
async def login_submit(request: Request):
    form = await form_body(request)
    username = form.get("username", "")
    password = form.get("password", "")
    request.session.clear()
    if platform_admin_ok(username, password):
        request.session[SESSION_AUTH] = AUTH_PLATFORM
        request.session[SESSION_USERNAME] = "Admin"
        return RedirectResponse("/admin", status_code=303)
    clinic_user = None
    login_block = None
    if db_ping():
        try:
            clinic_user, login_block = admin_db.verify_clinic_login(username, password)
        except Exception:
            clinic_user, login_block = None, None
    if login_block:
        return RedirectResponse(f"/login?error={login_block}", status_code=303)
    legacy_ok = False
    legacy_block = None
    if db_ping():
        legacy_ok, legacy_block = admin_db.legacy_clinic_login_ok(username, password)
    else:
        from app.admin_db import LEGACY_DEMO_USERNAMES

        legacy_ok = (
            username.strip().lower() in LEGACY_DEMO_USERNAMES and password == "123456"
        )
    if legacy_block:
        return RedirectResponse(f"/login?error={legacy_block}", status_code=303)
    if clinic_user or legacy_ok:
        request.session[SESSION_AUTH] = AUTH_CLINIC
        if clinic_user:
            request.session[SESSION_USER_ID] = clinic_user["id"]
            request.session[SESSION_CLINIC_ID] = clinic_user["clinic_id"]
            request.session[SESSION_CLINIC_NAME] = clinic_user["clinic_name"]
            request.session[SESSION_USERNAME] = clinic_user["username"]
        else:
            request.session[SESSION_USERNAME] = username.strip()
            if db_ping():
                demo = admin_db.legacy_demo_clinic()
                request.session[SESSION_CLINIC_ID] = demo["id"]
                request.session[SESSION_CLINIC_NAME] = demo["name"]
            else:
                request.session[SESSION_CLINIC_NAME] = admin_db.DEFAULT_CLINIC_NAME
        return RedirectResponse("/dashboard", status_code=303)
    return RedirectResponse("/login?error=1", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


ADMIN_NOTICES = {
    "clinic": "Clinic saved.",
    "user": "Clinic user saved.",
    "clinic-on": "Clinic activated.",
    "clinic-off": "Clinic deactivated.",
    "user-on": "User activated.",
    "user-off": "User deactivated.",
}


@app.get("/admin", response_class=HTMLResponse)
def admin_home(request: Request, saved: str = ""):
    guard = require_platform_admin(request)
    if guard:
        return guard
    clinics: list = []
    clinic_users: list = []
    overview: dict = {}
    if db_ping():
        clinics = admin_db.list_clinics()
        clinic_users = admin_db.list_clinic_users()
        try:
            overview = admin_db.platform_overview()
        except Exception:
            overview = {}
    return admin_render(
        request,
        "admin/index.html",
        admin_username=request.session.get(SESSION_USERNAME, "Admin"),
        overview=overview,
        clinics=clinics,
        clinic_users=clinic_users,
        notice=ADMIN_NOTICES.get(saved, ""),
        form_error="",
        clinic_form_error="",
        user_form_error="",
        clinic_form={},
        user_form={},
    )


@app.post("/admin/clinics")
async def admin_create_clinic(request: Request):
    guard = require_platform_admin(request)
    if guard:
        return guard
    form = await form_body(request)
    field_error = validate_clinic_fields(form.get("name", ""), form.get("phone", ""), form.get("address", ""))
    if not field_error and admin_db.clinic_phone_taken(form.get("phone", "")):
        field_error = "A clinic with this mobile number already exists."
    if field_error:
        return admin_render(
            request,
            "admin/index.html",
            admin_username=request.session.get(SESSION_USERNAME, "Admin"),
            clinics=admin_db.list_clinics() if db_ping() else [],
            clinic_users=admin_db.list_clinic_users() if db_ping() else [],
            form_error="",
            clinic_form_error=field_error,
            user_form_error="",
            clinic_form=form,
            user_form={},
            status_code=400,
        )
    try:
        admin_db.create_clinic(form.get("name", ""), form.get("phone", ""), form.get("address", ""))
    except ValueError as exc:
        return admin_render(
            request,
            "admin/index.html",
            admin_username=request.session.get(SESSION_USERNAME, "Admin"),
            clinics=admin_db.list_clinics() if db_ping() else [],
            clinic_users=admin_db.list_clinic_users() if db_ping() else [],
            form_error="",
            clinic_form_error=str(exc),
            user_form_error="",
            clinic_form=form,
            user_form={},
            status_code=400,
        )
    except Exception:
        return admin_render(
            request,
            "admin/index.html",
            admin_username=request.session.get(SESSION_USERNAME, "Admin"),
            clinics=admin_db.list_clinics() if db_ping() else [],
            clinic_users=admin_db.list_clinic_users() if db_ping() else [],
            form_error="Could not save clinic. Check database connection.",
            clinic_form_error="",
            user_form_error="",
            clinic_form=form,
            user_form={},
            status_code=503,
        )
    return RedirectResponse("/admin?saved=clinic", status_code=303)


@app.post("/admin/users")
async def admin_create_user(request: Request):
    guard = require_platform_admin(request)
    if guard:
        return guard
    form = await form_body(request)
    try:
        clinic_id = int(form.get("clinic_id", "0"))
    except ValueError:
        clinic_id = 0
    field_error = validate_clinic_user_fields(form.get("name", ""), form.get("phone", ""), form.get("email", ""))
    if not field_error:
        field_error = validate_username(form.get("username", ""))
    if field_error:
        return admin_render(
            request,
            "admin/index.html",
            admin_username=request.session.get(SESSION_USERNAME, "Admin"),
            clinics=admin_db.list_clinics() if db_ping() else [],
            clinic_users=admin_db.list_clinic_users() if db_ping() else [],
            form_error="",
            clinic_form_error="",
            user_form_error=field_error,
            clinic_form={},
            user_form=form,
            status_code=400,
        )
    try:
        admin_db.create_clinic_user(
            clinic_id,
            form.get("name", ""),
            form.get("username", ""),
            form.get("password", ""),
            form.get("email", ""),
            form.get("phone", ""),
        )
    except ValueError as exc:
        return admin_render(
            request,
            "admin/index.html",
            admin_username=request.session.get(SESSION_USERNAME, "Admin"),
            clinics=admin_db.list_clinics() if db_ping() else [],
            clinic_users=admin_db.list_clinic_users() if db_ping() else [],
            form_error="",
            clinic_form_error="",
            user_form_error=str(exc),
            clinic_form={},
            user_form=form,
            status_code=400,
        )
    except Exception:
        return admin_render(
            request,
            "admin/index.html",
            admin_username=request.session.get(SESSION_USERNAME, "Admin"),
            clinics=admin_db.list_clinics() if db_ping() else [],
            clinic_users=admin_db.list_clinic_users() if db_ping() else [],
            form_error="Could not save user. Check database connection.",
            clinic_form_error="",
            user_form_error="",
            clinic_form={},
            user_form=form,
            status_code=503,
        )
    return RedirectResponse("/admin?saved=user", status_code=303)


@app.post("/admin/clinics/{clinic_id}/active")
async def admin_clinic_active(request: Request, clinic_id: int):
    guard = require_platform_admin(request)
    if guard:
        return guard
    form = await form_body(request)
    active = form.get("active", "1") == "1"
    try:
        admin_db.set_clinic_active(clinic_id, active)
    except ValueError as exc:
        return admin_render(
            request,
            "admin/index.html",
            admin_username=request.session.get(SESSION_USERNAME, "Admin"),
            overview=admin_db.platform_overview() if db_ping() else {},
            clinics=admin_db.list_clinics() if db_ping() else [],
            clinic_users=admin_db.list_clinic_users() if db_ping() else [],
            form_error=str(exc),
            clinic_form_error="",
            user_form_error="",
            clinic_form={},
            user_form={},
            status_code=400,
        )
    notice = "clinic-on" if active else "clinic-off"
    return RedirectResponse(f"/admin?saved={notice}", status_code=303)


@app.post("/admin/users/{user_id}/active")
async def admin_user_active(request: Request, user_id: int):
    guard = require_platform_admin(request)
    if guard:
        return guard
    form = await form_body(request)
    active = form.get("active", "1") == "1"
    try:
        admin_db.set_clinic_user_active(user_id, active)
    except ValueError as exc:
        return admin_render(
            request,
            "admin/index.html",
            admin_username=request.session.get(SESSION_USERNAME, "Admin"),
            overview=admin_db.platform_overview() if db_ping() else {},
            clinics=admin_db.list_clinics() if db_ping() else [],
            clinic_users=admin_db.list_clinic_users() if db_ping() else [],
            form_error=str(exc),
            clinic_form_error="",
            user_form_error="",
            clinic_form={},
            user_form={},
            status_code=400,
        )
    notice = "user-on" if active else "user-off"
    return RedirectResponse(f"/admin?saved={notice}", status_code=303)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    clinic_id = resolve_clinic_id(request)
    today: list = []
    week_appts: list = []
    today_upcoming: list = []
    if db_ping():
        today = clinic_db.list_today_appointments(clinic_id)
        today_upcoming = [item for item in today if item.get("status") in ("pending", "confirmed")]
        week_appts = clinic_db.list_week_appointments(clinic_id)
    recent = clinic_db.list_patients("", clinic_id)[:5] if clinic_id else []
    return render(
        request,
        "dashboard.html",
        active="dashboard",
        today_upcoming=today_upcoming,
        week_appts=week_appts,
        recent=recent,
    )


@app.get("/patients", response_class=HTMLResponse)
def patients_page(request: Request, q: str = "", saved: str = ""):
    return render(
        request,
        "patients.html",
        active="patients",
        q=q,
        notice=NOTICES.get(saved, ""),
    )


@app.get("/patients/new", response_class=HTMLResponse)
def register_page(request: Request):
    return render(request, "register.html", active="patients", form_error="", form={})


@app.post("/patients/new")
async def register_submit(request: Request):
    form = await form_body(request)
    full_name = form.get("full_name", "").strip()
    dob = form.get("dob", "").strip()
    phone = form.get("phone", "").strip()
    email = form.get("email", "")
    address = form.get("address", "")
    notes = form.get("notes", "")
    error = validate_patient_fields(full_name, phone, address, email) or ""
    if not error and not clinic_db.parse_display_date(dob):
        error = "Choose date of birth from the calendar."
    if error:
        return render(
            request,
            "register.html",
            active="patients",
            form_error=error,
            form=form,
            status_code=400,
        )
    try:
        clinic_db.create_patient(
            full_name,
            dob,
            phone,
            resolve_clinic_id(request),
            email,
            address,
            notes,
        )
    except Exception:
        return render(
            request,
            "register.html",
            active="patients",
            form_error="Could not save patient. Check database connection.",
            form=form,
            status_code=503,
        )
    return RedirectResponse("/patients?saved=1", status_code=303)


def _patient_edit_context(
    request: Request,
    patient: dict,
    form_error: str = "",
    form: dict | None = None,
    status_code: int = 400,
):
    return render(
        request,
        "patient_edit.html",
        active="patients",
        patient=patient,
        form_error=form_error,
        form=form or {},
        status_code=status_code,
    )


@app.get("/patients/edit", response_class=HTMLResponse)
def patient_edit_page(request: Request, id: str = ""):
    try:
        patient_id = int(id)
    except ValueError:
        patient_id = 0
    if not db_ping() or patient_id <= 0:
        return RedirectResponse("/patients", status_code=303)
    clinic_id = resolve_clinic_id(request)
    patient = clinic_db.find_patient_by_id(patient_id, clinic_id)
    if not patient:
        return RedirectResponse("/patients", status_code=303)
    return render(request, "patient_edit.html", active="patients", patient=patient, form_error="", form={})


@app.post("/patients/edit")
async def patient_edit_submit(request: Request):
    form = await form_body(request)
    try:
        patient_id = int(form.get("patient_id", "0"))
    except ValueError:
        patient_id = 0
    clinic_id = resolve_clinic_id(request)
    patient = clinic_db.find_patient_by_id(patient_id, clinic_id) if patient_id else None
    if not patient:
        return RedirectResponse("/patients", status_code=303)
    full_name = form.get("full_name", "").strip()
    dob = form.get("dob", "").strip()
    phone = form.get("phone", "").strip()
    email = form.get("email", "")
    address = form.get("address", "")
    notes = form.get("notes", "")
    doctor = form.get("doctor", "")
    department = form.get("department", "General")
    status = form.get("status", "Active")
    error = validate_patient_fields(full_name, phone, address, email) or ""
    if not error and not clinic_db.parse_display_date(dob):
        error = "Choose date of birth from the calendar."
    if error:
        return _patient_edit_context(request, patient, form_error=error, form=form)
    try:
        clinic_db.update_patient(
            patient_id,
            clinic_id,
            full_name,
            dob,
            phone,
            email,
            address,
            notes,
            doctor,
            department,
            status,
        )
    except ValueError as exc:
        return _patient_edit_context(request, patient, form_error=str(exc), form=form)
    except Exception:
        return _patient_edit_context(
            request,
            patient,
            form_error="Could not save patient. Check database connection.",
            form=form,
        )
    back = "/history?patient=" + quote(full_name) + "&saved=patient"
    return RedirectResponse(back, status_code=303)


@app.get("/appointments", response_class=HTMLResponse)
def appointments_page(request: Request, booked: str = "", error: str = ""):
    clinic_id = resolve_clinic_id(request)
    today: list = []
    appointments_json = "[]"
    if db_ping():
        today = clinic_db.list_today_appointments(clinic_id)
        cal_start = date.today().replace(day=1) - timedelta(days=62)
        cal_end = date.today() + timedelta(days=186)
        cal_items = clinic_db.list_appointments_range(cal_start, cal_end, clinic_id)
        appointments_json = json.dumps(cal_items).replace("<", "\\u003c")
    notice = APPOINTMENT_NOTICE if booked else ""
    book_error = error.replace("+", " ") if error else ""
    return render(
        request,
        "appointments.html",
        active="appointments",
        today=today,
        appointments_json=appointments_json,
        notice=notice,
        book_error=book_error,
    )


@app.post("/appointments/quick-book")
async def quick_book(request: Request):
    form = await form_body(request)
    patient = form.get("patient", "").strip()
    date = form.get("date", "").strip()
    time = form.get("time", "").strip()
    doctor = form.get("doctor", "").strip()
    reason = form.get("reason", "").strip()
    payment = form.get("payment", "").strip()
    try:
        clinic_db.book_appointment(
            patient,
            date,
            time,
            doctor,
            reason,
            payment,
            resolve_clinic_id(request),
        )
    except ValueError as exc:
        msg = quote(str(exc))
        return RedirectResponse(f"/appointments?error={msg}", status_code=303)
    except Exception:
        msg = quote("Could not book appointment.")
        return RedirectResponse(f"/appointments?error={msg}", status_code=303)
    return RedirectResponse("/appointments?booked=1", status_code=303)


@app.post("/appointments/status")
async def appointment_status(request: Request):
    form = await form_body(request)
    try:
        appt_id = int(form.get("appointment_id", "0"))
    except ValueError:
        appt_id = 0
    action = form.get("action", "")
    next_url = form.get("next", "/appointments")
    try:
        clinic_db.set_appointment_status(appt_id, action, resolve_clinic_id(request))
    except Exception:
        pass
    return RedirectResponse(next_url or "/appointments", status_code=303)


@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request, patient: str = "", saved: str = "", error: str = "", msg: str = ""):
    clinic_id = resolve_clinic_id(request)
    record = clinic_db.empty_patient(patient)
    if db_ping() and patient.strip():
        found = clinic_db.find_patient_by_name(patient, clinic_id)
        if found:
            record = found
    notices = {
        "1": "Visit note saved.",
        "patient": "Patient details updated.",
        "rx": "Prescription saved.",
        "doc": "Document uploaded.",
    }
    notice = notices.get(saved, "")
    reason = request.query_params.get("reason", "")
    form_error = ""
    if error == "rx":
        form_error = msg.replace("+", " ") if msg else "Could not save prescription."
    elif error == "doc":
        if reason == "type":
            form_error = "Use PDF, Word, PNG, JPG or WEBP."
        elif reason == "size":
            form_error = "File must be under 5 MB."
        else:
            form_error = "Could not upload document."
    return render(
        request,
        "history.html",
        active="history",
        patient=record,
        notice=notice,
        form_error=form_error,
    )


@app.post("/history/visit")
async def history_visit(request: Request):
    form = await form_body(request)
    patient = form.get("patient", "").strip()
    title = form.get("title", "").strip()
    date = form.get("date", "").strip()
    notes = form.get("notes", "").strip()
    back = "/history?patient=" + quote(patient)
    if not title or not date or not notes:
        return RedirectResponse(back + "&error=1", status_code=303)
    try:
        clinic_db.add_visit_note(patient, title, date, notes, resolve_clinic_id(request))
    except Exception:
        return RedirectResponse(back + "&error=1", status_code=303)
    return RedirectResponse(back + "&saved=1", status_code=303)


@app.post("/history/prescription")
async def history_prescription(request: Request):
    form = await form_body(request)
    patient = form.get("patient", "").strip()
    date = form.get("date", "").strip()
    medication = form.get("medication", "").strip()
    dosage = form.get("dosage", "").strip()
    instructions = form.get("instructions", "").strip()
    back = "/history?patient=" + quote(patient)
    try:
        clinic_db.add_prescription(
            patient,
            date,
            medication,
            dosage,
            instructions,
            resolve_clinic_id(request),
        )
    except ValueError as exc:
        msg = quote(str(exc))
        return RedirectResponse(back + "&error=rx&msg=" + msg, status_code=303)
    except Exception:
        return RedirectResponse(back + "&error=rx", status_code=303)
    return RedirectResponse(back + "&saved=rx", status_code=303)


@app.post("/history/document")
async def history_document(
    request: Request,
    patient: str = Form(""),
    label: str = Form(""),
    file: UploadFile = File(...),
):
    patient = patient.strip()
    clinic_id = resolve_clinic_id(request)
    back = "/history?patient=" + quote(patient)
    if not patient:
        return RedirectResponse("/patients", status_code=303)
    record = clinic_db.find_patient_by_name(patient, clinic_id)
    if not record or not record.get("id"):
        return RedirectResponse(back + "&error=doc", status_code=303)
    original = (file.filename or "document").strip()
    suffix = Path(original).suffix.lower()
    if suffix not in ALLOWED_DOC_EXT:
        return RedirectResponse(back + "&error=doc&reason=type", status_code=303)
    data = await file.read()
    if not data or len(data) > MAX_DOC_BYTES:
        return RedirectResponse(back + "&error=doc&reason=size", status_code=303)
    stored = f"{uuid.uuid4().hex}{suffix}"
    folder = UPLOAD_ROOT / str(record["id"])
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / stored
    target.write_bytes(data)
    try:
        clinic_db.insert_patient_document(
            record["id"],
            original,
            stored,
            file.content_type or "application/octet-stream",
            len(data),
            label,
        )
    except Exception:
        if target.exists():
            target.unlink(missing_ok=True)
        return RedirectResponse(back + "&error=doc", status_code=303)
    return RedirectResponse(back + "&saved=doc", status_code=303)


@app.get("/patients/documents/{doc_id}")
def patient_document_download(request: Request, doc_id: int):
    meta = clinic_db.get_patient_document(doc_id, resolve_clinic_id(request))
    if not meta:
        return Response("Not found", status_code=404)
    path = UPLOAD_ROOT / str(meta["patient_id"]) / meta["stored_name"]
    if not path.is_file():
        return Response("Not found", status_code=404)
    return FileResponse(
        path,
        media_type=meta["content_type"],
        filename=meta["original_name"],
    )


@app.get("/account", response_class=HTMLResponse)
def account(request: Request):
    return render(request, "account.html", active="account")


@app.get("/support", response_class=HTMLResponse)
def support(request: Request):
    return render(request, "support.html", active="support")


@app.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request):
    return render(request, "privacy.html")


@app.get("/terms", response_class=HTMLResponse)
def terms(request: Request):
    return render(request, "terms.html")


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots(request: Request):
    base = str(request.base_url).rstrip("/")
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /login\n"
        "Disallow: /admin\n"
        "Disallow: /logout\n"
        "Disallow: /dashboard\n"
        "Disallow: /patients\n"
        "Disallow: /appointments\n"
        "Disallow: /history\n"
        "Disallow: /account\n"
        "Disallow: /support\n"
        "Disallow: /api/\n"
        f"Sitemap: {base}/sitemap.xml\n"
    )
    return PlainTextResponse(body)


@app.get("/sitemap.xml")
def sitemap(request: Request):
    base = str(request.base_url).rstrip("/")
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{base}/</loc></url>\n"
        f"  <url><loc>{base}/privacy</loc></url>\n"
        f"  <url><loc>{base}/terms</loc></url>\n"
        "</urlset>\n"
    )
    return Response(xml, media_type="application/xml")


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return render(request, "404.html", status_code=404)
    return HTMLResponse(str(exc.detail), status_code=exc.status_code)
