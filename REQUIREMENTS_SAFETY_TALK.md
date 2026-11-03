# Safety Talk Requirement — summary of staff source Excel (sheet `Safety Talk`)

## Confirmed in source
1. Select “รายงาน Safety Talk”, with action “+ สร้างรายงาน Safety Talk”.
2. Communication date (`talk_date`).
3. Select business UBE or UBS (`company`). The exact UBE/UBS department lists come from Excel and are in `config/departments.json`.
4. Reporter name (`reporter`).
5. Safety Talk topic (`topic`) and participant count (`participants`).
6. Evidence attachments: image/document (`evidence_files`).
7. Check required fields before submission. Show warning if incomplete and let user correct the form.
8. Store a report and generate its report ID; show a success message.
9. History / Dashboard: number of Safety Talks, number of participants, UBE/UBS breakdown.

## Workshop implementation choices (NOT claims from Excel)
- Use Streamlit + local CSV instead of production DB/SSO; user login is a mock requirement only, NOT an implemented secure authentication system.
- PNG/JPG/PDF whitelist, max 5 MB each, path sanitization; no network connection.
- Add monthly trend chart, report-history search, and CSV export as exercises to learn Pandas; these are workshop enhancements, not verified mandatory fields in the source sheet.
- Use synthetic sample data and a local URL `http://localhost:8501`.
- Not for production, no confidentiality or access-control guarantees. Deploy only after UBE IT/SHE review.

## Canonical report columns
`report_id,talk_date,company,department,reporter,topic,participants,evidence_files,created_at`

## Reference traceability
`draft  Flow Web Application_Safety(1).xlsx` > `Safety Talk` row 2 (flow), rows 5–6 (steps + company), rows 5–26 (departments).
