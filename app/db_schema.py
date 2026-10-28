from app.db import db_conn

EXTRA_DDL = [
    """
    CREATE TABLE IF NOT EXISTS prescriptions (
      id INT UNSIGNED NOT NULL AUTO_INCREMENT,
      patient_id INT UNSIGNED NOT NULL,
      prescribed_on DATE NOT NULL,
      medication VARCHAR(200) NOT NULL,
      dosage VARCHAR(120) NOT NULL,
      instructions TEXT NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (id),
      KEY idx_rx_patient (patient_id),
      CONSTRAINT fk_rx_patient FOREIGN KEY (patient_id) REFERENCES patients (id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS patient_documents (
      id INT UNSIGNED NOT NULL AUTO_INCREMENT,
      patient_id INT UNSIGNED NOT NULL,
      original_name VARCHAR(255) NOT NULL,
      stored_name VARCHAR(255) NOT NULL,
      content_type VARCHAR(120) NOT NULL,
      size_bytes INT UNSIGNED NOT NULL,
      label VARCHAR(160) NULL,
      uploaded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (id),
      KEY idx_docs_patient (patient_id),
      CONSTRAINT fk_docs_patient FOREIGN KEY (patient_id) REFERENCES patients (id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS clinics (
      id INT UNSIGNED NOT NULL AUTO_INCREMENT,
      name VARCHAR(160) NOT NULL,
      phone VARCHAR(32) NULL,
      address VARCHAR(255) NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (id),
      UNIQUE KEY uq_clinics_name (name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS clinic_users (
      id INT UNSIGNED NOT NULL AUTO_INCREMENT,
      clinic_id INT UNSIGNED NOT NULL,
      name VARCHAR(120) NOT NULL,
      username VARCHAR(80) NOT NULL,
      email VARCHAR(255) NOT NULL DEFAULT '',
      phone VARCHAR(32) NOT NULL DEFAULT '',
      password_hash VARCHAR(64) NOT NULL,
      role ENUM('admin', 'staff') NOT NULL DEFAULT 'admin',
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (id),
      UNIQUE KEY uq_clinic_users_username (username),
      KEY idx_clinic_users_clinic (clinic_id),
      CONSTRAINT fk_clinic_users_clinic FOREIGN KEY (clinic_id) REFERENCES clinics (id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
]


def _column_exists(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
        LIMIT 1
        """,
        (table, column),
    )
    return cur.fetchone() is not None


def _index_exists(cur, table: str, index_name: str) -> bool:
    cur.execute(
        """
        SELECT 1 FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND INDEX_NAME = %s
        LIMIT 1
        """,
        (table, index_name),
    )
    return cur.fetchone() is not None


def _default_clinic_id(cur) -> int:
    cur.execute("SELECT id FROM clinics ORDER BY id ASC LIMIT 1")
    row = cur.fetchone()
    if row:
        return row["id"]
    cur.execute(
        "INSERT INTO clinics (name, phone, address) VALUES ('Quantamloop Demo Clinic', NULL, NULL)"
    )
    return cur.lastrowid


def migrate_clinic_scope(cur) -> None:
    cur.execute("SHOW TABLES LIKE 'patients'")
    if not cur.fetchone():
        return
    default_clinic = _default_clinic_id(cur)
    if not _column_exists(cur, "patients", "clinic_id"):
        cur.execute("ALTER TABLE patients ADD COLUMN clinic_id INT UNSIGNED NULL AFTER id")
    cur.execute("UPDATE patients SET clinic_id = %s WHERE clinic_id IS NULL", (default_clinic,))
    cur.execute("ALTER TABLE patients MODIFY clinic_id INT UNSIGNED NOT NULL")
    if _index_exists(cur, "patients", "uq_patients_mrn"):
        cur.execute("ALTER TABLE patients DROP INDEX uq_patients_mrn")
    if not _index_exists(cur, "patients", "uq_patients_clinic_mrn"):
        cur.execute(
            "ALTER TABLE patients ADD UNIQUE KEY uq_patients_clinic_mrn (clinic_id, mrn)"
        )
    if not _index_exists(cur, "patients", "idx_patients_clinic"):
        cur.execute("ALTER TABLE patients ADD KEY idx_patients_clinic (clinic_id)")
    if not _index_exists(cur, "patients", "fk_patients_clinic"):
        try:
            cur.execute(
                """
                ALTER TABLE patients
                ADD CONSTRAINT fk_patients_clinic
                FOREIGN KEY (clinic_id) REFERENCES clinics (id)
                """
            )
        except Exception:
            pass

    if not _column_exists(cur, "doctors", "clinic_id"):
        cur.execute("ALTER TABLE doctors ADD COLUMN clinic_id INT UNSIGNED NULL AFTER id")
    cur.execute("UPDATE doctors SET clinic_id = %s WHERE clinic_id IS NULL", (default_clinic,))
    cur.execute("ALTER TABLE doctors MODIFY clinic_id INT UNSIGNED NOT NULL")
    if not _index_exists(cur, "doctors", "uq_doctors_clinic_name"):
        cur.execute("ALTER TABLE doctors ADD UNIQUE KEY uq_doctors_clinic_name (clinic_id, name)")
    if not _index_exists(cur, "doctors", "idx_doctors_clinic"):
        cur.execute("ALTER TABLE doctors ADD KEY idx_doctors_clinic (clinic_id)")
    if not _index_exists(cur, "doctors", "fk_doctors_clinic"):
        try:
            cur.execute(
                """
                ALTER TABLE doctors
                ADD CONSTRAINT fk_doctors_clinic
                FOREIGN KEY (clinic_id) REFERENCES clinics (id)
                """
            )
        except Exception:
            pass


def migrate_active_flags(cur) -> None:
    cur.execute("SHOW TABLES LIKE 'clinics'")
    if not cur.fetchone():
        return
    if not _column_exists(cur, "clinics", "is_active"):
        cur.execute(
            "ALTER TABLE clinics ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1 AFTER address"
        )
    cur.execute("UPDATE clinics SET is_active = 1 WHERE is_active IS NULL")
    if not _column_exists(cur, "clinic_users", "is_active"):
        cur.execute(
            "ALTER TABLE clinic_users ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1 AFTER role"
        )
    cur.execute("UPDATE clinic_users SET is_active = 1 WHERE is_active IS NULL")


def ensure_schema() -> None:
    try:
        with db_conn() as conn:
            with conn.cursor() as cur:
                for statement in EXTRA_DDL:
                    cur.execute(statement)
                migrate_clinic_scope(cur)
                migrate_active_flags(cur)
        from app.admin_db import ensure_builtin_clinic_users

        ensure_builtin_clinic_users()
    except Exception:
        pass
