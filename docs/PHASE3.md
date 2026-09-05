# Phase 3 — Placement Drives

**Refer to PROJECT_CONTEXT.md. Builds on Phase 2 (company must be approved to create drives).**

## Goal
Approved companies create placement drives; admin approves/rejects drives; students browse approved drives.

## Backend Tasks
1. `PlacementDrive` model: Drive ID, Company ID (FK), Job Title, Job Description, Eligibility (branch, min CGPA, eligible years), Application Deadline, Status (Pending/Approved/Closed/Rejected).
2. `POST /api/company/drives` — create drive (only if company.approval_status == Approved; else 403)
3. `GET /api/company/drives` — company lists own drives with applicant counts
4. `GET /api/admin/drives` — admin lists all drives, filter by status
5. `PUT /api/admin/drives/<id>/approve`
6. `PUT /api/admin/drives/<id>/reject`
7. `GET /api/student/drives` — student lists only Approved + not-past-deadline drives, supports eligibility-based filter/search (branch, CGPA, keyword)
8. `GET /api/drives/<id>` — drive detail (any authenticated role)

## Frontend (Vue) Tasks
1. Company: "Create Drive" form (blocked/hidden with message if company not yet approved).
2. Company: drive list view showing status + applicant count per drive.
3. Admin: drive approval queue (approve/reject buttons).
4. Student: drive browsing page — cards/list of approved drives, search + eligibility filter (branch/CGPA/year dropdown or text search).
5. Drive detail page/modal showing full JD + eligibility + deadline.

## Test / Definition of Done
- Company with Pending approval status cannot create a drive (API + UI both block it).
- Approved company creates a drive → shows as "Pending" in admin queue.
- Admin approves → drive now visible in student browse list (only if deadline not passed).
- Student search/filter returns correctly scoped results.
- Closed/rejected drives never appear in student list.