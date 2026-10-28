# Clinic CRM — deploy & test report

**Date:** 27 October 2026 (IST)  
**Environment:** GCP VM `qtl-clinic-crm` · **http://35.255.220.44:8000**  
**Deploy:** Full app tarball + API image rebuild (follow-up patch: template cache busters v14 on app pages)

---

## Deploy summary

| Item | Result |
|------|--------|
| Files synced to `/opt/clinic-crm` | OK |
| `docker compose build api` | OK |
| `docker compose up -d` | OK |
| `clinic-crm-api` | Up, port **8000** published |
| `clinic-crm-mysql` | Up, healthy, **3306 not published** to host |
| Container restart policy | `unless-stopped` (api + mysql) |

---

## Release markers (live)

| Check | Result |
|-------|--------|
| Marketing CSS `main.css?v=14` | Pass |
| Marketing JS `app.js?v=14` | Pass |
| App pages JS `app.js?v=14` | Pass (after template hotfix) |
| `page-marketing` class on home | Pass |
| Footer: Privacy policy & Terms | Pass |
| Patient registration DOB picker (`dob-picker`, `p2-value`) | Pass |
| Sitemap includes `/privacy` | Pass |

---

## HTTP route tests (GET)

All returned **200**:

- `/` (marketing)
- `/login`
- `/privacy`
- `/terms`
- `/dashboard`
- `/patients`
- `/patients/new`
- `/appointments`
- `/history`
- `/account`
- `/support`
- `/robots.txt`
- `/sitemap.xml`

Static assets: `/static/css/main.css?v=14`, `/static/js/app.js?v=14` — **200**

---

## Authentication (POST `/login`)

| Case | Expected | Result |
|------|----------|--------|
| `lakshmi` / `123456` | 303 → `/dashboard` | Pass |
| `dr.name@clinic.com` / `123456` | 303 → `/dashboard` | Pass |
| `lakshmi` / wrong password | 303 → `/login?error=1` | Pass |

---

## UI / functional tests (browser on live site)

| Case | Result | Notes |
|------|--------|--------|
| Home loads, legal links visible | Pass | |
| Privacy & Terms pages | Pass | GET 200 |
| Patient registration — DOB calendar | Pass | Opens ~25 years back; past dates only |
| **Add patient → patient list** | **Pass** | **MySQL** via `POST /patients/new`. Live: *SQL Test Patient* in `patients` table; list rendered from server. |
| **View patient / history** | **Pass** | `/history?patient=Ops%20Test%20Patient` loads profile, tabs (Visits, Prescriptions, Documents), “Book appointment” link. |
| **Appointments — quick book** | **Pass** | **MySQL** via `POST /appointments/quick-book`. Live: 11:00 SQL Test Patient in `appointments` + Today list. |
| Login via UI form | Not re-tested this run | POST `/login` with lakshmi/123456 **Pass** (curl); browser session was already authenticated |
| Dashboard stats after add | Pass | Counts from MySQL via server render |
| Support / Account forms | Not re-tested this run | Routes return 200 |
| Cancel / Attended appointment | Not re-tested this run | Book flow verified; action buttons present on booked row |
| Dashboard / empty data | Pass | Zeros and empty copy (dummy data cleared) |
| Mobile marketing layout | Pass (prior local QA) | Wider desktop marketing container up to ~1480px |
| Night VM schedule | Not re-tested this run | Existing policy `clinic-night-pause` unchanged |

**Storage (27 Oct update):** Patients, appointments, and visit notes are persisted in **MySQL** (`clinic_crm`). Browser `localStorage` is no longer used for clinical data.

---

## Database (MySQL on server)

| Table | Row count | Notes |
|-------|-----------|--------|
| `users` | 1 | Login user `lakshmi` / `dr.name@clinic.com` |
| `patients` | Live rows | Saved via `POST /patients/new` |
| `appointments` | Live rows | Saved via quick book + status updates |
| `doctors` | Auto-created | Created when booking by doctor name |

**Security:** MySQL port **3306 not reachable** from the public IP (connection timeout). Only API **8000** is exposed.

---

## Known limitations (by design today)

1. **Patient / appointment / visit notes** are stored in **MySQL** (PyMySQL, `DATABASE_URL` in Docker).
2. **Login** is still validated in app code; password hash in MySQL is not used by the UI yet.
3. **Week calendar navigation** is still a UI placeholder; the board shows the current Mon–Sat week from SQL.

---

## Recommended manual smoke test (5 min)

Steps 3–4 were executed on live on **27 Oct 2026** (see table above). Optional re-check:

1. Open http://35.255.220.44:8000 — check header, hero, footer legal links (hard refresh if cached).
2. Login: **lakshmi** / **123456** → Dashboard.
3. **Patients → New patient** → pick DOB from calendar → Save → confirm name on **Patient list**.
4. **Appointments → Quick book** → fill fields → confirm today list updates.
5. **Privacy** and **Terms** pages open from footer.

---

## Sign-off

| Area | Status |
|------|--------|
| Deploy | **Complete** |
| Public routes & login | **Pass** |
| Legal pages & sitemap | **Pass** |
| DOB date picker | **Pass** |
| Docker / MySQL exposure | **Pass** |
| Core CRM ops (add/view patient, book appointment) | **Pass** (MySQL-backed) |

**Tested by:** Cursor agent (automated HTTP + live browser E2E on http://35.255.220.44:8000)  
**Report files:** `DEPLOY_TEST_REPORT.md` · `DEPLOY_TEST_REPORT.html` (project root)
