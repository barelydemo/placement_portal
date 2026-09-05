# Phase 4 — Applications

**Refer to PROJECT_CONTEXT.md. Builds on Phase 3.**

## Goal
Students apply to drives (with eligibility + duplicate checks); companies view/shortlist/select applicants; students track status + history.

## Backend Tasks
1. `Application` model: Application ID, Student ID (FK), Drive ID (FK), Application Date, Status (Applied/Shortlisted/Selected/Rejected).
2. `POST /api/student/applications` — apply to a drive:
   - Reject if already applied to this drive (duplicate check)
   - Reject if student doesn't meet eligibility criteria (branch/CGPA/year check against drive)
   - Reject if deadline passed or drive not Approved
3. `GET /api/student/applications` — student's own applications with status + drive info (this doubles as "placement history")
4. `GET /api/company/drives/<id>/applications` — company views applicants for a specific drive
5. `PUT /api/company/applications/<id>/status` — company updates status (Shortlisted/Selected/Rejected), optionally schedule interview (add `interview_datetime` field if implementing scheduling)

## Frontend (Vue) Tasks
1. Student: "Apply" button on drive detail (disabled + reason shown if ineligible or already applied).
2. Student: "My Applications" page — list with status badges, filter by status, doubles as placement history view.
3. Company: applicant list per drive with student details, dropdown/buttons to update status.
4. Optional: simple interview schedule field/input on company side.

## Test / Definition of Done
- Ineligible student cannot apply (clear error message shown).
- Student cannot apply twice to same drive (button disabled + backend also rejects if bypassed).
- Eligible student applies successfully → appears in company's applicant list as "Applied".
- Company updates status → reflected instantly in student's "My Applications" view.
- Student's application history correctly lists all past + current applications with accurate statuses.