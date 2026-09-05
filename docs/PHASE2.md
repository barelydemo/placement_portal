# Phase 2 — Company Registration & Admin Approval

**Refer to PROJECT_CONTEXT.md. Builds on Phase 1 (auth must be working).**

## Goal
Company can view/edit its profile; Admin can view all companies, approve/reject them.

## Backend Tasks
1. `GET /api/company/profile` — company views own profile (auth: company role)
2. `PUT /api/company/profile` — company edits profile (HR contact, website, etc.)
3. `GET /api/admin/companies` — admin lists all companies with filters (status: pending/approved/rejected)
4. `PUT /api/admin/companies/<id>/approve` — admin approves
5. `PUT /api/admin/companies/<id>/reject` — admin rejects (optionally with reason)
6. `PUT /api/admin/companies/<id>/deactivate` — admin blacklist/deactivate toggle
7. Backend validation: required fields on company profile update.

## Frontend (Vue) Tasks
1. Company dashboard: show profile card with current approval status (Pending/Approved/Rejected badge).
2. Company profile edit form.
3. Admin dashboard: table/list of companies with status filter + search box (search by name — backend `?search=` param).
4. Approve / Reject / Deactivate buttons per row (admin) with confirmation.
5. Bootstrap badges/alerts to show status clearly.

## Test / Definition of Done
- Newly registered company shows "Pending" on its own dashboard.
- Admin sees the company in the pending list, approves it → status flips to "Approved" on both admin and company views.
- Reject flow works and reflects on company dashboard.
- Deactivate/blacklist a company → company can no longer log in or is flagged (decide and document behavior; enforce in Phase 1's auth check too).
- Search by company name on admin panel returns correct filtered results.