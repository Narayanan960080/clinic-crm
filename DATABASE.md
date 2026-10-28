# Clinic CRM database

MySQL 8 is running in Docker on the server. The script `sql/clinic_crm.sql` already created the database and loaded the sample rows.

## Connection

| Item | Value |
|---|---|
| Database name | `clinic_crm` |
| Username | `clinic` |
| Password | `clinic_pass` |
| Root username | `root` |
| Root password | `clinic_root` |
| Host inside Docker | `mysql` |
| Port inside Docker | `3306` |

MySQL is not open on the public internet. From the server terminal:

```bash
sudo docker exec -it clinic-crm-mysql mysql -uclinic -pclinic_pass clinic_crm
```

## App login stored in the database

| Item | Value |
|---|---|
| Username | `lakshmi` |
| Email | `dr.name@clinic.com` |
| Password | `123456` |
| Name | Dr. Name |
| Role | admin |

Sign in with username `lakshmi` and password `123456`. The same password also works with `dr.name@clinic.com`.

## Tables

There are **6 tables**.

| Table | What it stores | Rows |
|---|---|---|
| `users` | Clinic login account | 1 (`lakshmi`) |
| `doctors` | Doctors and departments | 0 |
| `patients` | Patient records | 0 |
| `appointments` | Booked visits, reason, status, payment | 0 |
| `visits` | Past visit notes | 0 |
| `support_tickets` | Support messages | 0 |
