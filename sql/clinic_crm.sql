-- Clinic CRM schema and sample data.
-- MySQL 8, utf8mb4, InnoDB.
-- Clinic login:
--   username lakshmi
--   email    dr.name@clinic.com
--   password 123456

CREATE DATABASE IF NOT EXISTS clinic_crm
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE clinic_crm;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TRIGGER IF EXISTS appointments_no_overlap_insert;
DROP TRIGGER IF EXISTS appointments_no_overlap_update;
DROP TABLE IF EXISTS support_tickets;
DROP TABLE IF EXISTS clinic_users;
DROP TABLE IF EXISTS clinics;
DROP TABLE IF EXISTS patient_documents;
DROP TABLE IF EXISTS prescriptions;
DROP TABLE IF EXISTS visits;
DROP TABLE IF EXISTS appointments;
DROP TABLE IF EXISTS patients;
DROP TABLE IF EXISTS doctors;
DROP TABLE IF EXISTS users;

SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE clinics (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(160) NOT NULL,
  phone VARCHAR(32) NULL,
  address VARCHAR(255) NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_clinics_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE clinic_users (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  clinic_id INT UNSIGNED NOT NULL,
  name VARCHAR(120) NOT NULL,
  username VARCHAR(80) NOT NULL,
  email VARCHAR(255) NOT NULL DEFAULT '',
  phone VARCHAR(32) NOT NULL DEFAULT '',
  password_hash VARCHAR(64) NOT NULL,
  role ENUM('admin', 'staff') NOT NULL DEFAULT 'admin',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_clinic_users_username (username),
  KEY idx_clinic_users_clinic (clinic_id),
  CONSTRAINT fk_clinic_users_clinic FOREIGN KEY (clinic_id) REFERENCES clinics (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE users (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(120) NOT NULL,
  username VARCHAR(80) NOT NULL,
  email VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  clinic_name VARCHAR(160) NOT NULL,
  phone VARCHAR(32) NOT NULL,
  role ENUM('admin') NOT NULL DEFAULT 'admin',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_username (username),
  UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE doctors (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  clinic_id INT UNSIGNED NOT NULL,
  name VARCHAR(120) NOT NULL,
  department VARCHAR(80) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_doctors_clinic_name (clinic_id, name),
  KEY idx_doctors_clinic (clinic_id),
  KEY idx_doctors_department (department),
  CONSTRAINT fk_doctors_clinic FOREIGN KEY (clinic_id) REFERENCES clinics (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE patients (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  clinic_id INT UNSIGNED NOT NULL,
  mrn VARCHAR(32) NOT NULL,
  full_name VARCHAR(160) NOT NULL,
  dob DATE NULL,
  gender ENUM('female', 'male', 'other', 'unspecified') NOT NULL DEFAULT 'unspecified',
  phone VARCHAR(32) NULL,
  email VARCHAR(255) NULL,
  address VARCHAR(255) NULL,
  notes TEXT NULL,
  status ENUM('active', 'follow_up', 'new', 'inactive') NOT NULL DEFAULT 'new',
  doctor_id INT UNSIGNED NULL,
  department VARCHAR(80) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_patients_clinic_mrn (clinic_id, mrn),
  KEY idx_patients_clinic (clinic_id),
  KEY idx_patients_name (full_name),
  KEY idx_patients_phone (phone),
  KEY idx_patients_email (email),
  KEY idx_patients_status (status),
  KEY idx_patients_doctor (doctor_id),
  KEY idx_patients_department (department),
  CONSTRAINT fk_patients_clinic FOREIGN KEY (clinic_id) REFERENCES clinics (id),
  CONSTRAINT fk_patients_doctor FOREIGN KEY (doctor_id) REFERENCES doctors (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE appointments (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  patient_id INT UNSIGNED NOT NULL,
  doctor_id INT UNSIGNED NOT NULL,
  start_time DATETIME NOT NULL,
  end_time DATETIME NOT NULL,
  reason VARCHAR(160) NOT NULL,
  status ENUM('pending', 'confirmed', 'completed', 'cancelled') NOT NULL DEFAULT 'pending',
  payment_status ENUM('paid', 'pending', 'unpaid') NOT NULL DEFAULT 'pending',
  PRIMARY KEY (id),
  KEY idx_appointments_patient (patient_id),
  KEY idx_appointments_doctor_time (doctor_id, start_time),
  KEY idx_appointments_status (status),
  KEY idx_appointments_payment (payment_status),
  CONSTRAINT fk_appointments_patient FOREIGN KEY (patient_id) REFERENCES patients (id),
  CONSTRAINT fk_appointments_doctor FOREIGN KEY (doctor_id) REFERENCES doctors (id),
  CONSTRAINT chk_appointment_range CHECK (end_time > start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE visits (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  patient_id INT UNSIGNED NOT NULL,
  doctor_id INT UNSIGNED NULL,
  visit_date DATETIME NOT NULL,
  title VARCHAR(160) NOT NULL,
  notes TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_visits_patient_date (patient_id, visit_date),
  KEY idx_visits_doctor (doctor_id),
  CONSTRAINT fk_visits_patient FOREIGN KEY (patient_id) REFERENCES patients (id),
  CONSTRAINT fk_visits_doctor FOREIGN KEY (doctor_id) REFERENCES doctors (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE prescriptions (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE patient_documents (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE support_tickets (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id INT UNSIGNED NOT NULL,
  subject VARCHAR(160) NOT NULL,
  message TEXT NOT NULL,
  status ENUM('open', 'closed') NOT NULL DEFAULT 'open',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_support_user (user_id),
  KEY idx_support_status (status),
  CONSTRAINT fk_support_user FOREIGN KEY (user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELIMITER $$

CREATE TRIGGER appointments_no_overlap_insert
BEFORE INSERT ON appointments
FOR EACH ROW
BEGIN
  IF NEW.status <> 'cancelled' AND EXISTS (
    SELECT 1
    FROM appointments AS existing
    WHERE existing.doctor_id = NEW.doctor_id
      AND existing.status <> 'cancelled'
      AND existing.start_time < NEW.end_time
      AND existing.end_time > NEW.start_time
  ) THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'That doctor already has an appointment in this time slot.';
  END IF;
END$$

CREATE TRIGGER appointments_no_overlap_update
BEFORE UPDATE ON appointments
FOR EACH ROW
BEGIN
  IF NEW.status <> 'cancelled' AND EXISTS (
    SELECT 1
    FROM appointments AS existing
    WHERE existing.id <> NEW.id
      AND existing.doctor_id = NEW.doctor_id
      AND existing.status <> 'cancelled'
      AND existing.start_time < NEW.end_time
      AND existing.end_time > NEW.start_time
  ) THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'That doctor already has an appointment in this time slot.';
  END IF;
END$$

DELIMITER ;

INSERT INTO users (name, username, email, password_hash, clinic_name, phone, role) VALUES
  (
    'Dr. Name',
    'lakshmi',
    'dr.name@clinic.com',
    '$2b$12$TXQIrc6Ip4ao1Nobvetn9uwe/l1spAIFMSgjHs77icQ4hRYAMAs5e',
    'Clinic name',
    '+91 98450 10000',
    'admin'
  );
