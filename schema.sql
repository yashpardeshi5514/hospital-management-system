-- schema.sql: create database and required tables
CREATE DATABASE IF NOT EXISTS hospital_db;
USE hospital_db;

-- Table for storing user chat history
CREATE TABLE IF NOT EXISTS user_history (
  history_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(100),
  message TEXT,
  is_user BOOLEAN,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS patients (
  patient_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100),
  age INT,
  gender VARCHAR(10),
  contact VARCHAR(20),
  disease VARCHAR(100),
  doctor_assigned VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS staff (
  staff_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100),
  role VARCHAR(50),
  contact VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS appointments (
  appointment_id INT AUTO_INCREMENT PRIMARY KEY,
  patient_id INT,
  staff_id INT,
  appointment_date DATE,
  appointment_time TIME,
  FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
  FOREIGN KEY (staff_id) REFERENCES staff(staff_id) ON DELETE SET NULL
);
