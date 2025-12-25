# 🏥 Hospital Management System

A **Hospital Management System** developed using **Python and Flask** to manage hospital operations such as patient records, doctor details, and appointment scheduling.
This project is ideal for **college projects, resume building, and backend development practice and learning**.

---

## 📌 Project Overview

The Hospital Management System is designed to automate and simplify hospital workflows.
It provides a structured way to store and manage patient information, doctor data, and appointments using a database-driven backend.
The project follows a modular architecture and supports Docker-based deployment.

---

## 🚀 Features

* 👤 Patient Management (Add and View patient records)
* 🩺 Doctor Management
* 📅 Appointment Scheduling
* 🤖 AI Chat Module (Basic assistant)
* 🗄️ Database integration using SQL
* 🐳 Docker support for deployment
* 📁 Clean and modular project structure

---

## 🛠️ Tech Stack

* **Backend:** Python, Flask
* **Database:** MySQL / SQLite
* **Frontend:** HTML, CSS
* **DevOps:** Docker
* **Version Control:** Git & GitHub

---

## 📂 Project Structure

```
hospital-management-system/
│
├── app.py                # Main Flask application
├── db.py                 # Database connection logic
├── ai_chat.py            # AI chat module
├── schema.sql            # Database schema
├── requirements.txt      # Python dependencies
├── Dockerfile            # Docker configuration
├── Procfile              # Deployment configuration
├── static/               # Static files (HTML, CSS, Images)
├── README.md             # Project documentation
├── .gitignore
└── .dockerignore
```

---

## ⚙️ Installation & Setup (Local Machine)

### Clone the Repository

```
git clone https://github.com/yashpardeshi5514/hospital-management-system.git
cd hospital-management-system
```

### Create and Activate Virtual Environment

```
python -m venv venv
venv\Scripts\activate
```

### Install Dependencies

```
pip install -r requirements.txt
```

### Setup Database

* Create a database (MySQL or SQLite)
* Execute the SQL file:

```
schema.sql
```

### Run the Application

```
python app.py
```

Open your browser and visit:

```
http://127.0.0.1:5000/
```

---

## 🐳 Run Using Docker

```
docker build -t hospital-management-system .
docker run -p 5000:5000 hospital-management-system
```

---

## 🔮 Future Enhancements

* 🔐 User Authentication (Admin, Doctor, Patient)
* 💳 Billing and Payment Module
* 🏥 Pharmacy Management
* 📊 Dashboard and Reports
* ☁️ Cloud Deployment (AWS / Render)

---

## 👨‍💻 Author

**Yash Pardeshi**
📍 Maharashtra, India
