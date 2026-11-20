# Timesheet & Workforce Management Platform (Chronos)

Production-grade, role-based weekly timesheet and approval platform tailored for an SAP consulting firm, built from [timesheet_workforce_management_platform_specification.md](timesheet_workforce_management_platform_specification.md) and [timesheet_openapi_django.yaml](timesheet_openapi_django.yaml).

---

## Architecture Overview

* **Backend (`backend/`):** Python 3.12 + Django 5.2 modular monolith with Django REST Framework (`drf-spectacular` OpenAPI 3.1.0), Argon2 password hashing, JWT authentication (`djangorestframework-simplejwt` with immediate deactivation enforcement), `ETag`/`If-Match` & `version` optimistic concurrency, `Idempotency-Key` protection, append-only `AuditEvent` and `ApprovalEvent` ledgers, and a fault-isolated notification outbox (`apps/notifications`).
  * Domain apps: `accounts`, `settings_app`, `clients`, `projects`, `assignments`, `timesheets`, `approvals`, `reports`, `notifications`, `audit`.
  * Integration boundaries: `integrations/sap` (SAP CATS staging mapper) & `integrations/ai` (scoped AI service boundary) and `apps/accounts/auth_backends.py` (`OIDCIdentityAdapter` for Microsoft Entra ID / SAP IAS).
* **Frontend (`frontend/`):** React 19 + TypeScript + Vite 6 accessible enterprise UI with `Temporal.PlainDate` location-agnostic week calculations, native `<dialog>` modals, container-query responsive tables, and post-interaction ARIA validation.
* **Documentation:** See [docs/CONTRACT_FIXES.md](docs/CONTRACT_FIXES.md) for OpenAPI 3.1 contract fixes and baseline policy defaults for open `TBD` items.

---

## Repository Structure

```text
├── backend/                  # Modular Django + DRF backend
│   ├── apps/                 # Domain apps (accounts, projects, timesheets, approvals, etc.)
│   ├── common/               # ErrorEnvelope, RequestID middleware, RBAC, ETag & idempotency
│   ├── config/               # Settings (base/dev/test/prod), Celery, WSGI/ASGI, URLs
│   ├── integrations/         # SAP CATS staging & AI service boundary stubs
│   └── tests/                # Pytest suite (AC-01..AC-10, security, concurrency, OpenAPI drift)
├── frontend/                 # React 19 + TypeScript + Vite 6 web client
├── docs/                     # Contract fixes and baseline policy documentation
├── .github/workflows/ci.yml  # CI pipeline (PostgreSQL 16 + Ruff + Pytest + Vitest + Vite build)
├── docker-compose.yml        # Full containerized stack (PostgreSQL, Redis, Django, Celery, Nginx)
├── timesheet_openapi_django.yaml
└── timesheet_workforce_management_platform_specification.md
```

---

## Quick Start Locally

### Prerequisites
* **Python** 3.12+
* **Node.js** 22+ and **npm**

> By default, local development (`config.settings.dev`) uses SQLite (`backend/db.sqlite3`) automatically when `DATABASE_URL` is unset, so no external database installation is required to run locally.

### 1. First-Time Setup (If Cloned Fresh)

**Windows (PowerShell):**
```powershell
# Backend virtual environment & packages
python -m venv backend\.venv
backend\.venv\Scripts\pip install -r backend\requirements.txt

# Frontend packages
cd frontend
npm install
cd ..
```

**macOS / Linux:**
```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt

cd frontend
npm install
cd ..
```

### 2. Migrate, Seed Demo Data & Run the Backend

**Windows (PowerShell):**
```powershell
backend\.venv\Scripts\python backend\manage.py migrate
backend\.venv\Scripts\python backend\manage.py seed_demo_data
backend\.venv\Scripts\python backend\manage.py runserver 8000
```

**macOS / Linux:**
```bash
backend/.venv/bin/python backend/manage.py migrate
backend/.venv/bin/python backend/manage.py seed_demo_data
backend/.venv/bin/python backend/manage.py runserver 8000
```

### 3. Run the Frontend Dev Server (New Terminal)

```bash
cd frontend
npm run dev
```

### 4. Open Local Endpoints

| Service | URL |
| :--- | :--- |
| **Web Application (Vite UI)** | `http://localhost:5173` |
| **Interactive API Docs (Swagger UI)** | `http://127.0.0.1:8000/api/docs/` |
| **OpenAPI 3.1 Schema** | `http://127.0.0.1:8000/api/schema/` |
| **Readiness Probe** | `http://127.0.0.1:8000/api/v1/health/ready` |
| **Django Admin** | `http://127.0.0.1:8000/admin/` |

### Demo Accounts (Password: `DemoPass123!`)

| Role | Email | Code | Scope |
| :--- | :--- | :--- | :--- |
| **Employee** | `consultant@sapconsult.example.com` | `EMP-003` | Weekly timesheet entry, submit, returned/approved views |
| **Employee** | `abap.dev@sapconsult.example.com` | `EMP-004` | Submitted timesheet awaiting manager review |
| **Approver** | `manager@sapconsult.example.com` | `EMP-002` | Team approval queue, reject with reason, tasks & assignments |
| **Admin** | `admin@sapconsult.example.com` | `EMP-001` | Users, clients, projects, settings, reopen, and audit log |
| **Management Viewer** | `director@sapconsult.example.com` | `EMP-005` | Department-scoped (`SAP Delivery`) reports and CSV export |

*(Quick-sign-in buttons for primary demo roles are also shown on the `/login` page.)*

---

## Running Tests & Quality Checks

**Backend (from repository root):**
```powershell
backend\.venv\Scripts\ruff check backend
backend\.venv\Scripts\python backend\manage.py makemigrations --check --dry-run
backend\.venv\Scripts\python backend\manage.py check
backend\.venv\Scripts\python backend\manage.py spectacular --validate --fail-on-warn --file backend\_tmp_schema.yaml
backend\.venv\Scripts\pytest -c backend\pyproject.toml backend\tests -v
```

**Frontend (from `frontend/`):**
```bash
npx tsc --noEmit
npm test
npm run build
```

---

## Containerized Production Deployment (PostgreSQL + Redis + Nginx)

```bash
cp .env.example .env
# Update DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, and database credentials in .env before production use
docker compose up --build
```

* Frontend Nginx serves the SPA on port `8080` and proxies `/api/`, `/admin/`, and `/static/` to Django/Gunicorn on port `8000`.
* Optional scheduled reminders can be triggered via Celery Beat or cron:
  ```bash
  python backend/manage.py send_timesheet_reminders
  ```
