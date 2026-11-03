# AGENTS.md — UBE Safety Talk Workshop (training sandbox)

- Language: Explain in Thai; code identifiers in English.
- Framework: Python 3.11+, Streamlit, Pandas; run locally on Windows with `python -m streamlit run app.py`.
- Scope: ONLY Safety Talk in Day 1. Do not add Login, real database, cloud deploy, BBS/PPE/Envi, or production integrations unless instructor explicitly asks.
- Source requirements: `REQUIREMENTS_SAFETY_TALK.md`, which summarizes the Safety Talk worksheet supplied by staff. Keep UBE/UBS organization lists in `config/departments.json`.
- Do not rename existing CSV columns or delete sample data. Actual submissions go to `data/reports.csv`; sample values live in `data/sample_safety_talk.csv`.
- Require date, company, department, reporter, topic, participants (>0); allow optional JPEG/PNG/PDF attachments under 5 MB each. Report ID unique `ST-YYYYMMDD-NNNN`. Files only under local `data/uploads/`.
- Dashboard totals = number of reports, sum of participants, UBE and UBS report counts; monthly activity = report count by month. Do not invent completion percentages (source did not specify workflow statuses).
- Local demonstration only. No real company personal information or confidential document uploads. Never invent official UBE domains/URLs.
- For EACH change: read current files, explain short plan, edit ONLY files needed, show changed files and the exact test command, avoid large refactors and unrelated extra features.
- Follow instructor checkpoints. Do not install global packages or execute destructive commands.
