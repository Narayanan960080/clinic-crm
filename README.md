# Clinic CRM

UI preview for Clinic CRM, a product of Quantamloop Innovation Private Limited. Screens follow the marketing, login, dashboard, patients, appointments, history, account and support layouts.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000

Sign in with username `lakshmi` and password `123456`. The same password also works with `dr.name@clinic.com`.

## Docker

MySQL 8 and the web app:

```bash
docker compose up --build
```

Open http://localhost:8000. MySQL is on port 3306. The database name, user, and password are in `.env.example` (`clinic_crm` / `clinic` / `clinic_pass`). On the first start, Docker loads `sql/clinic_crm.sql`.

Stop the local preview first if port 8000 is already in use.

## SQL

`sql/clinic_crm.sql` creates the tables and sample patients, doctors, appointments, visits, and one support ticket. It rejects a second appointment for the same doctor when the times overlap.

Load it into a MySQL 8 server you already have:

```bash
mysql -u root -p < sql/clinic_crm.sql
```

## GitHub & deploy

Source lives on GitHub; pushes to `main` deploy to the GCP VM via GitHub Actions. See [docs/CICD.md](docs/CICD.md) for secrets and one-time server git setup.
