# Placement Portal Application (PPA) — Project Context

> **Read this file before starting ANY phase.** This is the single source of truth for constraints. Every phase markdown assumes these rules apply.

## 1. Overview
Build a web application where an **Institute Admin**, **Companies**, and **Students** manage campus placement activities: company approval, placement drives, student applications, tracking, and reporting.

## 2. Mandatory Tech Stack (STRICT — no substitutions)
| Layer | Technology | Notes |
|---|---|---|
| API Backend | **Flask** | All business logic/API here |
| Frontend UI | **VueJS** | Via CDN only for entry point. NOT for full UI unless Vue CLI used (optional, not required) |
| Templates | **Jinja2** | Only as the HTML entry point, not to render dynamic UI |
| CSS/Styling | **Bootstrap** | ONLY allowed CSS framework — no Tailwind, no MUI, etc. |
| Database | **SQLite** | ONLY allowed DB — created **programmatically** via models/migrations, never via DB Browser or manual tools |
| Caching | **Redis** | For performance, with cache expiry |
| Async/Batch Jobs | **Redis + Celery** | For scheduled and triggered background jobs |

⚠️ **No other framework/library is allowed** apart from the above (plus optional: Chart.js for charts, JWT libs, resume/PDF libs as needed for optional features).

## 3. Roles
1. **Admin (Institute Placement Cell)** — pre-existing, single superuser, seeded programmatically after DB creation. **No admin registration/signup allowed.**
2. **Company** — registers, needs admin approval, creates drives (need admin approval), manages applicants.
3. **Student** — self-registers, browses approved drives, applies, tracks status.

## 4. Core Data Entities (minimum — can extend)
- **User** (unified model differentiating role: admin/company/student)
- **CompanyProfile**: Company ID, Company Name, HR Contact, Website, Approval Status
- **PlacementDrive**: Drive ID, Company ID, Job Title, Job Description, Eligibility Criteria (branch, CGPA, year), Application Deadline, Status (Pending/Approved/Closed)
- **Application**: Application ID, Student ID, Drive ID, Application Date, Status (Applied/Shortlisted/Selected/Rejected)

## 5. Core Functional Rules
- Role-based access control + authentication (Flask session or **JWT**)
- Companies register → **Admin must approve** before company can create drives
- Drives created by company → **Admin must approve** before visible to students
- Students **cannot apply twice** to the same drive
- Eligibility validation before allowing an application
- Admin can search/blacklist/deactivate companies & students
- Admin dashboard: total students, total companies, total drives, reports/stats
- Company dashboard: profile, created drives, applicant counts
- Student dashboard: approved drives, eligibility filter/search, applied status, placement history, resume upload

## 6. Backend/Async Jobs (Required)
| Job | Type | Trigger | Detail |
|---|---|---|---|
| Daily Reminders | Scheduled (Celery beat) | Daily | Remind students of upcoming deadlines via email/SMS/Google Chat webhook |
| Monthly Activity Report | Scheduled (Celery beat) | 1st of month | HTML (or PDF) report to admin via email: drives conducted, students applied/selected |
| Export Applications CSV | User-triggered async | Student clicks export | Celery task, alert once done |

## 7. Performance
- Add Redis caching on read-heavy endpoints (dashboards/stats/listings)
- Implement cache expiry
- Optimize API response times

## 8. Optional/Recommended (implement after core is done)
- PDF reports (choice of HTML or PDF) using a PDF lib + Chart.js for charts
- Single responsive UI (mobile + desktop)
- Frontend validation (HTML5/JS) + backend validation (in API)
- Dummy offer letter generator OR ATS-style resume checker
- Any other value-add feature

## 9. Explicit Non-Negotiables
- Admin: only one, only login (no registration route at all)
- DB tables: created via code (SQLAlchemy models / migrations), never manually
- Local machine demo must work end-to-end
- Wireframe is a flow reference only — exact UI replication NOT required

## 10. Suggested Folder Structure
```
placement_portal/
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── models/
│   ├── routes/
│   ├── services/         # business logic
│   ├── tasks/            # celery tasks
│   ├── cache/            # redis helpers
│   └── seed.py           # admin seeding script
├── frontend/
│   ├── templates/
│   │   └── index.html    # Jinja2 entry point only
│   └── static/
│       ├── js/           # Vue app(s)
│       └── css/
└── requirements.txt
```

## 11. How to Use the Phase Files
Work through `phase0_setup.md` → `phase7_polish_optional.md` **in order**. Each phase is self-contained: implement it, test it fully (as instructed in that file), THEN move to the next. Do not skip ahead. Each phase file repeats only the constraints relevant to it — this file is the full reference if anything is ambiguous.