# Phase 6 — Backend Jobs (Celery + Redis)

**Refer to PROJECT_CONTEXT.md. Builds on Phase 5. Celery instance already set up in Phase 0.**

## Goal
Implement all three required background jobs.

## Task A — Scheduled: Daily Reminders
- Celery Beat scheduled task, runs daily at a configured time.
- Finds students with upcoming/nearing application deadlines (define a window, e.g., deadline within next 2 days) for drives they're eligible for but haven't applied to, OR reminders for drives they've applied to with upcoming interview — document your chosen logic.
- Sends via **one of**: email (SMTP/Flask-Mail), SMS (any free/mock provider), or Google Chat Webhook.
- For local demo: OK to use a mock/log-based "send" if no real credentials available, but structure the code as if it sends for real (document this clearly in the report's AI/LLM + implementation notes).

## Task B — Scheduled: Monthly Activity Report
- Celery Beat task, runs on the 1st of every month (also add a manually-triggerable admin endpoint for demo purposes: `POST /api/admin/reports/monthly/trigger`).
- Report content: number of drives conducted, number of students applied, number of students selected (for the past month).
- Format: HTML email (PDF optional — see Phase 7).
- Sent to Admin's email via Flask-Mail/SMTP (or mock/log for demo).

## Task C — User-Triggered Async: Export Applications as CSV
- `POST /api/student/applications/export` — triggers Celery task, returns task ID immediately (don't block).
- Celery task generates CSV: Student ID, Company Name, Drive Title, Application Status, Dates.
- `GET /api/tasks/<task_id>/status` — poll endpoint for task completion.
- On completion, send an alert (in-app notification via polling, or email) with download link: `GET /api/student/applications/export/<task_id>/download`.

## Frontend (Vue) Tasks
1. Student dashboard: "Export My Applications" button → triggers export, shows spinner/status, then download link/alert when ready (poll `/api/tasks/<id>/status` every few seconds).
2. Admin: "Trigger Monthly Report Now" button (demo convenience) with success toast.

## Test / Definition of Done
- Celery worker + Celery beat both run without errors (`celery -A ... worker` and `celery -A ... beat`).
- Manually trigger daily reminder task → correct students identified and (mock/real) message sent — verify via logs.
- Manually trigger monthly report → correct stats computed and (mock/real) email sent.
- Export CSV: click export → task runs async → CSV downloadable with correct data.
- Export flow doesn't block the UI/API (verify by checking response returns immediately, not after task completes).