# Hospital AI + DBMS Project (ready-to-open)

This folder contains a simple hospital management system combining:
- **AI-style chatbot** (natural-language commands using `ai_chat.py`)
- **DBMS backend** (MySQL) via `app.py` (Flask) and `db.py`

## What I created for you
- `app.py`            -> Flask app (already uses `ai_chat.py` and `db.py`)
- `ai_chat.py`        -> Simple NLP/regex parser (extracts structured data)
- `db.py`             -> MySQL connection helper (reads env vars)
- `static/index.html` -> Frontend chat UI (open at /)
- `schema.sql`        -> SQL to create `patients`, `staff`, `appointments`
- `requirements.txt`  -> Python dependencies

## Download the ZIP and open in VS Code
1. Download the zip file provided with this message.
2. Open VS Code → `File` → `Open Folder...` → select the extracted `hospital_ai_dbms` folder.

## Step-by-step: setup database & run in VS Code (Linux / macOS)
1. Open terminal in VS Code (``Ctrl+` ``).
2. Create virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4. Install MySQL server (if not installed). On Ubuntu:
    ```bash
    sudo apt update
    sudo apt install mysql-server
    sudo mysql_secure_installation
    ```
5. Create database and tables (method A: MySQL client):
    ```bash
    mysql -u root -p < schema.sql
    ```
   or (method B: open MySQL shell)
    ```sql
    mysql -u root -p
    CREATE DATABASE hospital_db;
    USE hospital_db;
    SOURCE /full/path/to/schema.sql;
    ```
6. Set environment variables (example):
    ```bash
    export DB_HOST=localhost
    export DB_USER=root
    export DB_PASS=your_root_password
    export DB_NAME=hospital_db
    export DB_PORT=3306
    ```
7. Run the Flask app:
    ```bash
    python app.py
    ```
   Open: `http://localhost:5000` in your browser.

## Step-by-step: setup on Windows (PowerShell)
1. Open terminal in VS Code.
2. Create venv:
    ```powershell
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    ```
3. Install:
    ```powershell
    pip install -r requirements.txt
    ```
4. Create DB (using MySQL Workbench or `mysql` client):
    ```powershell
    mysql -u root -p < schema.sql
    ```
5. Set env vars (PowerShell):
    ```powershell
    $env:DB_HOST='localhost'
    $env:DB_USER='root'
    $env:DB_PASS='your_root_password'
    $env:DB_NAME='hospital_db'
    $env:DB_PORT='3306'
    ```
6. Run:
    ```powershell
    python app.py
    ```

## User Chat History

All user chat interactions are saved in the `user_history` table in the database. Each message (from user or bot) is stored with a timestamp and user ID.

### How to view chat history
- In the chat box, type:
    ```
    Show history
    ```
    This will return the last 50 messages for the current user (based on `user_id` sent in the API request, or 'anonymous' if not provided).

### How it works
- Every message sent to `/api/chat` is saved to the database.
- Bot responses are also saved.
- You can customize the `user_id` by sending it in the JSON payload (e.g., `{ "user_id": "alice", "message": "Show history" }`).

---

## How to add records (examples you can paste into the chat box or call via POST /api/chat)
- Add patient:
  ```
  Add patient name Riya age 22 gender female contact +919876543210 disease fever doctor Dr. Patel
  ```
- Add staff:
  ```
  Add staff name Dr. Sharma role Physician contact +919812345678
  ```
- Schedule appointment:
  ```
  Schedule appointment patient_id 1 staff_id 1 date 2025-10-13 time 10:30
  ```
- Show patients / staff / appointments:
  ```
  Show patients
  Show staff
  Show appointments
  ```

## Testing the API with curl
```bash
curl -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"message":"Add patient name Riya age 22 gender female contact +919876543210 disease fever doctor Dr. Patel"}'
```

## Notes & next steps
- `db.py` reads DB credentials from environment variables. You can also hardcode for local testing (not recommended).
- If you want the chatbot to do *smarter* NLP (intent classification / entity extraction), you can later integrate an NLP library (spaCy or a hosted model).
- If VS Code shows linting errors, install the Python extension and select the venv interpreter.

-- End of README --

## Deploying online (quick guides)

Below are two simple options to make this app available online.

Option A — Deploy to Render (recommended for quick deploy)
- Create a new Web Service on Render.
- Connect to your GitHub repo or push this project to a new repo.
- Set the build command: `pip install -r requirements.txt`
- Set the start command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 3`
- Add environment variables on Render:
    - DB_HOST, DB_USER, DB_PASS, DB_NAME, DB_PORT
    - Optional: OPENAI_API_KEY (if you want server-side OpenAI polishing)
- For the database, either use Render's managed PostgreSQL / MySQL (configure credentials), or provide access to an external managed MySQL instance.

Option B — Docker (build and run on any host)
- Build the Docker image:
    ```powershell
    docker build -t hospital_ai_dbms:latest .
    ```
- Run the container (link to an external MySQL or run a MySQL container):
    ```powershell
    docker run -e DB_HOST=<host> -e DB_USER=<user> -e DB_PASS=<pass> -e DB_NAME=<db> -e DB_PORT=3306 -p 5000:5000 hospital_ai_dbms:latest
    ```

Security notes (important)
- Do NOT enable the OpenAI option if the data contains private or regulated PII you are not allowed to send to external services.
- Protect the app with authentication or restrict network access before exposing it publicly. Simple options:
    - Place behind a VPN or private VPC.
    - Add HTTP basic auth or API key checks on `/api/chat`.
    - Use a managed DB with proper network rules.

If you want, I can:
- Add a simple API key check to `/api/chat` and instructions for usage.
- Create Docker Compose with a MySQL service for local testing.
- Add CI/CD config (GitHub Actions) to build and push Docker images.
