# Phase 7 — Polish, Validation & Optional Features

**Refer to PROJECT_CONTEXT.md. Builds on Phase 6. This is the final phase before submission prep.**

## Required Polish Tasks
1. **Frontend validation** on ALL forms (login, register, company profile, drive creation, application) using HTML5 attributes and/or JS — required fields, email format, number ranges (CGPA), date validity.
2. **Backend validation** on every API endpoint that accepts input — reject malformed/missing data with clear 400 error messages (don't just rely on frontend).
3. **Responsive UI** — test all pages on mobile width and desktop width using Bootstrap grid/utilities; fix any broken layouts.
4. **Resume upload** for students (file upload endpoint, store path in Student profile, allow download/view).
5. Final UI aesthetics pass: consistent navbar per role, consistent color scheme, loading states, error toasts/alerts across the app.
6. Full regression test of Phases 1–6 together (see checklist below).

## Optional Features (pick at least one, per project doc)
Choose ONE (or more) of:
- **PDF monthly reports** — let admin/student choose HTML or PDF (use a PDF lib e.g. WeasyPrint/ReportLab); add Chart.js visuals to the report.
- **Dummy offer letter generator** — company selects a student → generates a templated offer letter (PDF or HTML) with student/drive details.
- **ATS-style resume checker** — simple keyword/skill match scoring between uploaded resume text and a drive's job description.
- Any other feature you think adds value (document reasoning in project report).

## Full Regression Checklist (run before final submission)
- [ ] Admin login works; no admin registration route exists anywhere (UI or API)
- [ ] Student & company registration + login work
- [ ] Company approval flow (approve/reject/deactivate) works end-to-end
- [ ] Drive creation blocked until company approved; drive approval flow works
- [ ] Student can only see Approved, non-expired drives with working search/filter
- [ ] Application flow: eligibility check, duplicate prevention, status updates all correct
- [ ] Admin dashboard stats accurate and cached (Redis) with expiry
- [ ] Search + blacklist/deactivate work for both students and companies
- [ ] Daily reminder job runs and targets correct students
- [ ] Monthly report job runs and computes correct stats
- [ ] CSV export is async (Celery), non-blocking, downloadable with correct data
- [ ] All forms have frontend + backend validation
- [ ] App is usable on both mobile and desktop widths
- [ ] Entire demo runs on local machine from a clean clone/setup (test this literally — fresh clone, fresh venv, run `seed.py`, start Flask + Redis + Celery worker + beat, use the app)

## Submission Prep (per project doc — not code, just reminders)
- Project report (≤5 pages): student details, problem approach, AI/LLM declaration, frameworks used, ER diagram, API endpoints list, video link.
- Folder structure matches the doc's suggested structure (frontend/backend split).
- Single zip file for submission.
- Video: intro (30s) → approach (30s) → key features (90s) → extra features (30s), max 5-10 min, uploaded with public link.