# Coaching Manager

A web-based admin portal for managing a coaching centre — students, teachers, fee collection, and weekly schedules — built with **FastAPI** and **PostgreSQL**.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy, Alembic |
| Auth | JWT (PyJWT) + Bcrypt password hashing |
| Database | PostgreSQL |
| Frontend | Jinja2 templates, Vanilla JS |
| Server | Uvicorn |

---

## Key Features

### 🔐 Authentication
- Secure admin login with JWT-based session cookies
- Bcrypt-hashed passwords
- Change password from the sidebar or top bar
- Auto-seeded default admin account on first startup

### 📊 Dashboard
- Live KPI cards — active students, active faculty, monthly fees collected, and pending dues
- Unified directory search across students, subjects, and faculty timetables in a single input
- Debounced real-time search results with no page reload

### 👨‍🎓 Students & Enrollments
- Add, edit, and soft-delete student profiles (name, grade, guardian info)
- Enroll students into subjects with a specific teacher and monthly fee
- View all active enrollments per student with their combined monthly fee
- Filter and search students by name, phone, or grade

### 👩‍🏫 Teachers & Schedules
- Add, edit, and manage teacher profiles
- Assign weekly schedule slots per teacher (subject, grade/batch, day, start/end time)
- View each teacher's full weekly timetable and number of active students
- Filter and search teachers by name, subject, or phone

### 💰 Payments & Fee Ledger
- Monthly fee ledger with per-subject paid/unpaid breakdown per student
- Collect partial or full fees; statuses update automatically (`UNPAID → PARTIAL → PAID`)
- Filter ledger by billing month and fee status (All / Unpaid / Partial / Paid)
- Recent payment receipts table with receipt numbers, amounts, and subjects

### 🗂️ Audit Log
- Automatic change tracking on every `CREATE`, `UPDATE`, and `DELETE` across all domain tables
- Logs admin username, IP address, user-agent, and a before/after field diff
- Sensitive fields (e.g. password hashes) are redacted in audit records
- Auth events (login, logout, password change) are explicitly logged

### 🖥️ UI / UX
- Responsive retractable sidebar (260 px ↔ collapsed) with push-reflow on desktop and off-canvas overlay on mobile
- Sticky top command bar with breadcrumb navigation and quick-action buttons
- Toast notification system for success and error feedback
- Anti-FOUC sidebar state restoration from `localStorage` before first paint

---

## Getting Started

### Prerequisites
- Python 3.10+
- PostgreSQL database

### Setup

```bash
# 1. Clone the repo and enter the directory
cd "Student_management"

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables � edit .env with your credentials
#    Required: DB_USER / DB_PASSWORD (superuser, used only by migration.py)
#              MIGRATOR_DB_USER / MIGRATOR_DB_PASSWORD (DDL role)
#              APP_DB_USER / APP_DB_PASSWORD (DML role, used by FastAPI)

# 5. Run the migration script once (as your superuser)
#    Creates the two roles, grants privileges, and builds all tables.
python migration.py

# 6. Start the server � connects as the least-privilege app role
uvicorn app.main:app --reload
```

The app will be available at `http://localhost:8000`.  
API docs are at `http://localhost:8000/docs`.

---

## Environment Variables

| Variable | Used by | Description |
|---|---|---|
| `DB_HOST` / `DB_PORT` / `DB_NAME` | `migration.py` + app | PostgreSQL host, port, database name |
| `DB_USER` / `DB_PASSWORD` | `migration.py` only | Superuser � creates roles and grants |
| `MIGRATOR_DB_USER` / `MIGRATOR_DB_PASSWORD` | `migration.py` only | DDL role � creates / alters tables |
| `APP_DB_USER` / `APP_DB_PASSWORD` | FastAPI app | DML-only role � `SELECT/INSERT/UPDATE/DELETE` |
| `SECRET_KEY` | App | JWT signing secret |
| `DEFAULT_ADMIN_USERNAME` / `DEFAULT_ADMIN_PASSWORD` | App | Seeded admin account credentials |

---

## Project Structure

```
app/
├── api/v1/          # REST API routers (auth, students, teachers, schedules, payments)
├── core/            # Config, database, security, audit engine
├── crud/            # Database query helpers
├── models/          # SQLAlchemy ORM models
├── schemas/         # Pydantic request/response schemas
├── static/          # CSS and JavaScript
├── templates/       # Jinja2 HTML templates
├── web/             # Server-side rendered page routes
└── main.py          # App entry point & lifespan hooks
```

---

## API Health Check

```
GET /health
→ { "status": "ok", "app": "Coaching Manager" }
```
