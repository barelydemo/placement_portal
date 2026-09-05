# Phase 5 — Admin Dashboard, Search, Blacklist, Redis Caching

**Refer to PROJECT_CONTEXT.md. Builds on Phase 4.**

## Goal
Complete admin oversight tools + introduce Redis caching for performance on read-heavy endpoints.

## Backend Tasks
1. `GET /api/admin/stats` — returns total students, total companies, total drives (+ any extra useful stats: pending approvals count, total applications, etc.)
   - **Cache this endpoint in Redis** with a TTL (e.g., 60s), invalidate/refresh on relevant writes (or just let it expire).
2. `GET /api/admin/students` — list/search all students (by name/branch/email)
3. `GET /api/admin/companies` — extend Phase 2's endpoint with full-text search if not already done
4. `PUT /api/admin/students/<id>/deactivate` — blacklist/deactivate a student
5. Ensure deactivated students/companies are blocked at login (enforce in auth middleware from Phase 1).
6. Add Redis caching to at least one more read-heavy endpoint (e.g., `GET /api/student/drives` listing) with sensible TTL + cache key strategy (e.g., per-filter-combo key).

## Frontend (Vue) Tasks
1. Admin dashboard homepage: stat cards (students/companies/drives/pending approvals).
2. Admin: students table with search + deactivate button.
3. Admin: companies table with search (from Phase 2) — confirm still working.
4. Visual indicator (loading/cached) not required, but ensure dashboard loads fast on repeat visits.

## Test / Definition of Done
- Admin dashboard stats load correctly and match actual DB counts.
- Second load of stats within TTL window is served from cache (verify via Redis logs/monitor or added debug log).
- After TTL expiry or a relevant change, stats refresh correctly (not stuck stale).
- Deactivated student cannot log in; deactivated company cannot log in or create drives.
- Search endpoints return correct partial-match results for both students and companies.