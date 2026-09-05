# Phase 0 — Project Setup

**Refer to PROJECT_CONTEXT.md for full constraints before implementing.**

## Goal
Set up a working skeleton: folder structure, Flask app factory, SQLite DB (created programmatically), base User model, Redis connection, Celery instance — nothing functional yet, just a running skeleton.

## Tasks
1. Create folder structure exactly as in PROJECT_CONTEXT.md section 10.
2. Set up Python virtual environment + `requirements.txt` with: Flask, Flask-SQLAlchemy, Flask-JWT-Extended (or Flask session-based auth), redis, celery, python-dotenv, flask-cors (if needed).
3. Create Flask app factory (`app.py` / `create_app()` pattern) with config for SQLite DB path.
4. Create base `User` model (unified model) with fields: id, name, email, password_hash, role (enum: admin/company/student), is_active, created_at.
5. Write a `seed.py` script that:
   - Creates all DB tables programmatically (`db.create_all()` or migrations)
   - Seeds the **single Admin user** (hardcoded/env-based credentials) if not already present
6. Set up Redis connection config (`REDIS_URL` in `.env`/config).
7. Set up Celery app instance (broker + backend = Redis), just the instance — no tasks yet.
8. Create Jinja2 entry point `index.html` that loads Vue via CDN and mounts an empty Vue app (just "Hello PPA" render) to confirm Vue is wired up.
9. Add Bootstrap via CDN link in `index.html`.

## Test / Definition of Done
- `flask run` starts the server with no errors.
- Visiting `/` renders the Jinja2 page with Vue mounted (see "Hello PPA" on screen, styled with Bootstrap).
- Running `seed.py` creates `placement.db` with tables and exactly one Admin row — confirm via query, not DB Browser.
- Redis connection test (ping) succeeds.
- Celery worker starts without errors (`celery -A ... worker`), even with zero tasks.

## Do NOT
- Do not build any auth, business logic, or Vue routing yet — that's Phase 1+.