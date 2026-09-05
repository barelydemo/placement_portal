# Placement Portal Application (PPA)

A campus placement management portal where an **Institute Admin**, **Companies** and
**Students** manage the full placement cycle: company approval, placement drives,
applications, tracking, reporting and background jobs.

---

## Tech stack

| Layer | Technology |
|---|---|
| API backend | Flask 3 (application factory pattern) |
| Frontend | Vue 3 via CDN (no build step, no vue-router) |
| Templating | Jinja2 — single HTML entry point only |
| Styling | Bootstrap 5 via CDN |
| Database | SQLite, created programmatically from SQLAlchemy models |
| Auth | JWT (Flask-JWT-Extended) + Redis token blocklist |
| Caching | Redis, with TTL + version-counter invalidation |
| Background jobs | Celery + Celery Beat (Redis broker/backend) |

No other frameworks are used. SMTP and Google Chat delivery use the Python
standard library, so there are no extra dependencies for notifications.

---

## Project structure

```
├── backend/
│   ├── app.py                 # create_app() factory, error handlers, asset() helper
│   ├── config.py              # all configuration, loaded from .env
│   ├── seed.py                # creates tables + seeds the single admin
│   ├── models/                # User, CompanyProfile, StudentProfile, PlacementDrive, Application
│   ├── routes/                # auth, admin, company, student, drives, tasks
│   ├── services/              # business logic (auth, drives, applications, reports, …)
│   ├── cache/                 # Redis client, cache helpers, JWT blocklist
│   └── tasks/                 # Celery app + the three background jobs
├── frontend/
│   ├── templates/index.html   # Jinja2 entry point (mounts Vue)
│   └── static/
│       ├── js/app.js          # root Vue app + hash router
│       ├── js/store.js        # shared auth state + API helper
│       ├── js/components/     # one component per view
│       └── css/style.css
├── scripts/                   # test_phase1.ps1 … test_phase7.ps1
├── docs/                      # project context + phase specifications
├── var/                       # generated at runtime (exports, resumes, logs) — gitignored
└── requirements.txt
```

---

## Prerequisites

- **Python 3.10+** (developed and verified on 3.14)
- **Redis** running on `localhost:6379` — required for caching, JWT logout and Celery
  - Docker: `docker run -d --name ppa-redis -p 6379:6379 redis:7-alpine`

---

## Setup

```powershell
# 1. Virtual environment
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. Configuration
Copy-Item .env.example .env

# 3. Create the database and seed the admin
.\venv\Scripts\python.exe -m backend.seed
```

`seed.py` is idempotent — it creates any missing tables, adds any new columns, and
only ever creates one admin. Run it again after pulling changes.

Expected output:

```
[seed] Tables ensured: applications, company_profiles, placement_drives, student_profiles, users
[seed] Admin created  -> admin@ppa.local
[verify] OK: exactly one Admin user exists.
```

---

## Running

Four processes. Redis first, then:

```powershell
# Terminal 1 — web app
.\venv\Scripts\flask.exe run --port 5001

# Terminal 2 — Celery worker  (-P solo is required on Windows)
.\venv\Scripts\celery.exe -A backend.tasks.celery_app:celery_app worker --loglevel=info -P solo

# Terminal 3 — Celery beat (scheduled jobs)
.\venv\Scripts\celery.exe -A backend.tasks.celery_app:celery_app beat --loglevel=info
```

Open **http://127.0.0.1:5001**

> Port 5001 is used because port 5000 is often already taken. Any free port works.

### Default admin

| Email | Password |
|---|---|
| `admin@ppa.local` | `Admin@123` |

There is **no admin registration** — by design, the admin exists only via `seed.py`.
Students and companies self-register through the UI.

`GET /api/health` reports database and Redis connectivity.

---

## Roles and flows

**Admin** — approves/rejects companies and drives, searches and blacklists students and
companies, views portal statistics, triggers background jobs.

**Company** — registers → waits for admin approval → posts drives (which the admin also
approves) → reviews applicants, shortlists/selects, schedules interviews, generates offer
letters. Editing an approved profile sends it back to *Pending* for re-review.

**Student** — registers, maintains profile and resume, browses approved drives with
eligibility filtering, applies (blocked if ineligible, duplicate, or past deadline),
tracks application status and exports history to CSV.

---

## Background jobs

| Job | Schedule | What it does |
|---|---|---|
| Daily reminders | Beat, 09:00 daily | For each active student: approved drives closing within `REMINDER_WINDOW_DAYS` that they are **eligible for and have not applied to**, plus interviews in the same window. Students with nothing to report are skipped. |
| Monthly report | Beat, 1st at 06:00 | HTML activity report for the previous month (drives conducted, students applied, students selected) emailed to the admin. |
| CSV export | User-triggered | Student clicks Export → returns a task id immediately → worker builds the CSV → student polls and downloads. |

Both scheduled jobs can be triggered on demand from the admin **Overview** page.

### Notifications

Delivery is pluggable via `NOTIFICATION_BACKEND`:

- **`log`** (default) — writes the fully rendered message to `var/notifications.log`.
  No credentials needed; the demo runs on this.
- **`smtp`** — real email. Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`,
  `SMTP_PASSWORD`, `SMTP_USE_TLS`, `MAIL_FROM`. (Gmail requires an App Password.)
- **`chat`** — Google Chat webhook. Set `GOOGLE_CHAT_WEBHOOK_URL`.

Switching modes is configuration only — no code changes.

---

## Caching

- `GET /api/admin/stats` and `GET /api/student/drives` are cached in Redis.
- Every cached response carries an **`X-Cache: HIT|MISS`** header.
- Keys embed a namespace version counter; any relevant write bumps it, so a change is
  reflected immediately rather than waiting for the TTL to lapse.
- The student drives cache is keyed **per student and per filter combination**, because
  the payload contains caller-specific eligibility.
- If Redis is unavailable the app **fails open** — correct data, just uncached.

---

## API reference

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Student or company only (admin rejected) |
| POST | `/api/auth/login` | All roles; returns JWT |
| GET | `/api/auth/me` | Current user |
| POST | `/api/auth/logout` | Revokes the token via Redis |

### Admin
| Method | Endpoint |
|---|---|
| GET | `/api/admin/stats` *(cached)* |
| GET | `/api/admin/companies` `?status=&search=&active=` |
| PUT | `/api/admin/companies/<id>/approve` · `/reject` · `/deactivate` |
| GET | `/api/admin/students` `?search=&active=` |
| PUT | `/api/admin/students/<id>/deactivate` |
| GET | `/api/admin/drives` `?status=&search=` |
| PUT | `/api/admin/drives/<id>/approve` · `/reject` |
| POST | `/api/admin/reports/monthly/trigger` · `/api/admin/reminders/trigger` |

### Company
| Method | Endpoint |
|---|---|
| GET / PUT | `/api/company/profile` |
| POST / GET | `/api/company/drives` |
| PUT | `/api/company/drives/<id>/close` |
| GET | `/api/company/drives/<id>/applications` |
| PUT | `/api/company/applications/<id>/status` |
| GET | `/api/company/applications/<id>/resume` |
| GET | `/api/company/applications/<id>/offer-letter` `?ctc=&joining_date=&location=` |

### Student
| Method | Endpoint |
|---|---|
| GET / PUT | `/api/student/profile` |
| POST | `/api/student/resume` · GET `/api/student/resume/download` |
| GET | `/api/student/drives` `?search=&branch=&cgpa=&eligible_only=` *(cached)* |
| POST / GET | `/api/student/applications` `?status=` |
| POST | `/api/student/applications/export` |
| GET | `/api/student/applications/export/<task_id>/download` |

### Shared
| Method | Endpoint |
|---|---|
| GET | `/api/drives/<id>` — role-scoped detail |
| GET | `/api/tasks/<task_id>/status` — background task polling |
| GET | `/api/health` |

All errors return JSON: `400` validation, `401` unauthenticated, `403` wrong role or
forbidden action, `404` not found, `409` duplicate application, `413` file too large.

---

## Tests

Seven PowerShell suites covering **286 checks** against a running server.
Phase 6 also needs the Celery worker.

```powershell
.\scripts\test_phase1.ps1 -BaseUrl "http://127.0.0.1:5001"   # 27  auth + RBAC
.\scripts\test_phase2.ps1 -BaseUrl "http://127.0.0.1:5001"   # 44  company approval
.\scripts\test_phase3.ps1 -BaseUrl "http://127.0.0.1:5001"   # 49  placement drives
.\scripts\test_phase4.ps1 -BaseUrl "http://127.0.0.1:5001"   # 42  applications
.\scripts\test_phase5.ps1 -BaseUrl "http://127.0.0.1:5001"   # 41  stats + caching
.\scripts\test_phase6.ps1 -BaseUrl "http://127.0.0.1:5001"   # 37  Celery jobs
.\scripts\test_phase7.ps1 -BaseUrl "http://127.0.0.1:5001"   # 46  resume, offer letter, validation
```

---

## Configuration reference

All settings live in `.env` (see `.env.example` for the annotated version).

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY`, `JWT_SECRET_KEY` | dev values | **Change for any real deployment** |
| `JWT_ACCESS_TOKEN_HOURS` | `8` | Token lifetime |
| `DATABASE_PATH` | `placement.db` | SQLite file (relative to project root) |
| `REDIS_URL` | `redis://localhost:6379/0` | Cache |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | db 1 / db 2 | Celery |
| `CACHE_STATS_TTL` / `CACHE_DRIVES_TTL` | `60` | Cache lifetimes (seconds) |
| `NOTIFICATION_BACKEND` | `log` | `log` · `smtp` · `chat` |
| `REMINDER_WINDOW_DAYS` | `2` | Reminder look-ahead |
| `REMINDER_HOUR` / `MONTHLY_REPORT_HOUR` | `9` / `6` | Beat schedule times |
| `MAX_RESUME_MB` | `5` | Upload size limit |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | `admin@ppa.local` / `Admin@123` | Seeded admin |

---

## Notes and known behaviour

- **Deadlines** are stored in server-local time. A date-only deadline means the *end* of
  that day, so the deadline day itself is inclusive.
- **Editing an approved company profile** resets it to *Pending* for admin re-review.
- **Offer letters** are generated as printable HTML (browser → Print → Save as PDF) and
  only for candidates with status *Selected*. They are clearly marked as specimens.
- **Deactivating** a student or company blocks login immediately and invalidates tokens
  already issued.
- A background task stuck at `PENDING` means **no Celery worker is running**.
- The JWT is stored in `localStorage`, so a refresh keeps the session. This project
  intentionally skips httpOnly cookies and CSRF handling given its scope.
- After changing frontend files, static URLs are automatically cache-busted by file
  modification time, so a hard refresh should not be necessary.
