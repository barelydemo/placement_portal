# Phase 1 — Authentication & Role Setup

**Refer to PROJECT_CONTEXT.md for full constraints. Builds on Phase 0.**

## Goal
Full working auth: student/company self-registration, login for all three roles, JWT-protected routes, role-based access control. Admin has NO registration route.

## Backend Tasks
1. Extend `User` model if needed; add `CompanyProfile` and `Student` profile models linked to `User` (1:1).
2. API endpoints:
   - `POST /api/auth/register` — role = student or company only (reject if role=admin attempted)
   - `POST /api/auth/login` — returns JWT (or sets session) for all roles including admin
   - `GET /api/auth/me` — returns current logged-in user + role
   - `POST /api/auth/logout`
3. Role-based decorator/middleware (`@role_required('admin')` etc.) to protect routes later.
4. Password hashing (werkzeug/bcrypt).
5. Confirm seeded Admin can log in via same `/login` endpoint — no separate admin login route needed, just no admin signup.

## Frontend (Vue) Tasks
1. Login page/component (single form, role auto-detected from backend response).
2. Register page/component with role toggle: Student / Company (two different forms — different fields).
3. Store JWT/session in memory (Vue state) — call `/api/auth/me` on load to check session.
4. Simple role-based redirect after login: admin → `/admin`, company → `/company`, student → `/student` (routes can be placeholder pages for now).
5. Basic Bootstrap styling on forms + HTML5 frontend validation (required fields, email format, password length).

## Test / Definition of Done
- Register a new student → row created, password hashed, default status active.
- Register a new company → row created in CompanyProfile with approval_status = "Pending".
- Login as admin (seeded credentials) → success, redirected to admin placeholder page.
- Login as student/company → success, redirected to respective placeholder page.
- Attempt to register with role=admin → rejected with clear error.
- Attempt to access a role-protected placeholder route with wrong role's token → 403.
- Invalid login (wrong password) → proper error message, no crash.