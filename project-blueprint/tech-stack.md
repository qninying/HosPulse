# HosPulse: Tech Stack

Grounded in `project-blueprint/architecture.md`. Scale assumed from that file: one solo founder, a handful of management-company customers, tens to low hundreds of hospitals, monthly uploads, weekly briefings, and a public snapshot covering every US rural hospital. No patient data.

## Technology table

| Component | Recommended Technology | Fit | Why | Learn More |
|---|---|---|---|---|
| Public Health Snapshot Page | Next.js (hosted on Vercel) | 🟢 | It can pre-build one fast page per hospital that search engines index (list in results), so a CEO who googles their hospital finds HosPulse, and Vercel's free tier covers this traffic. | "Explain Next.js to me like I'm new to web frameworks, using my HosPulse public Health Snapshot as the example." |
| Operator Portal | Next.js (same app as the snapshot) | 🟢 | Keeping the private portal in the same codebase as the public page means one app for Claude Code to maintain instead of two. | "Show me how one Next.js app can serve both a public page and a login-protected portal, using HosPulse as the example." |
| Access Control | Supabase Auth | 🟢 | It handles sign-in and works directly with the database's row-level security (a database rule that only returns rows belonging to the signed-in customer), so one management company can never see another's hospitals; Clerk was the runner-up. | "Explain Supabase Auth and row-level security to me, using HosPulse's rule that each management company only sees its own hospitals." |
| Metrics Database (relational) | PostgreSQL (managed by Supabase) | 🟢 | Monthly numbers per hospital fit naturally into tables, Postgres handles this volume easily, and Supabase's free and entry plans keep costs near zero at the start. | "Explain PostgreSQL to me like I'm new to databases, using HosPulse's monthly hospital metrics as the example." |
| Export File Storage | Supabase Storage | 🟢 | It gives private file buckets (locked folders) in the same account as the database and sign-in, so there is one fewer vendor to manage. | "Explain how Supabase Storage keeps uploaded files private, using HosPulse's monthly hospital exports as the example." |
| HCRIS Importer | Python with DuckDB | 🟢 | DuckDB (a small database engine that runs inside a script) reads the large CMS cost report files in seconds on an ordinary laptop, with no server to run. | "Teach me DuckDB with Python using the CMS HCRIS cost report files for HosPulse as the example." |
| Normalizer | Python with pandas | 🟢 | pandas (the standard Python library for working with tables of data) is the most common tool for reshaping messy exports into one standard format, and Claude Code writes and tests it well. | "Show me how pandas can map exports from different hospital billing systems into one standard format for HosPulse." |
| Upload Intake + PHI Guard | Microsoft Presidio | 🟡 | It is an open-source tool that detects personal information like names and birth dates, but no detector is perfect, so it must be paired with a strict list of allowed columns and anything unexpected rejected. | "Explain how Microsoft Presidio detects patient data, and how HosPulse should combine it with an allowed-columns check to reject uploads." |
| Scheduler | GitHub Actions scheduled workflows | 🟡 | It runs the weekly analysis, nightly processing of new uploads, and quarterly public data refresh for free, but runs can start a few minutes late and customer financial data passes through GitHub's machines, which is acceptable only while there is no patient data. | "Explain GitHub Actions scheduled workflows to me, using HosPulse's weekly briefing run as the example." |
| KPI + Early-Warning Engine | Python (plain rule functions tested with pytest) | 🟢 | Writing each warning rule as a small, tested Python function (pytest is Python's standard testing tool) keeps every flag explainable and traceable to a number, which is what an operator acting on it needs. | "Show me how to write early-warning rules as small tested Python functions for HosPulse, like falling days cash on hand." |
| AI Briefing Agent | Claude Sonnet 5 (Anthropic API) | 🟢 | A weekly briefing for a few dozen hospitals is a small, cheap job that Sonnet writes well, and Opus would add cost without a real quality gain for this task. | "Explain how to prompt Claude Sonnet 5 to write HosPulse's weekly briefing using only the numbers it is given." |
| Email Delivery Service | Resend | 🟢 | It has a simple API (a way for code to send a request to a service), a free tier that covers a few thousand emails a month, and good inbox delivery for a small weekly send. | "Explain how Resend sends emails from code, using HosPulse's weekly hospitals-at-risk briefing as the example." |
| Cost Report Co-pilot (Phase 3) | Claude Opus 5.5 (Anthropic API) | 🟡 | Finding missed reimbursement needs careful reasoning over detailed accounting lines, which justifies the most capable model, but it costs more per run and is not needed until Phase 3. | "Explain how Claude Opus 5.5 could review a hospital cost report for missed reimbursement in HosPulse, with a human expert confirming every finding." |

## Not applicable

- **CMS HCRIS public cost report files**: an external government dataset HosPulse only downloads.
- **Public visitor**: a person, not a technology choice.
- **Management company operator**: the customer, not a technology choice.

---

**Summary:** 16 components (13 technology decisions + 3 not applicable). Technology table: 🟢 10 · 🟡 3 · 🔴 0.
