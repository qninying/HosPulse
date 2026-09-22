# HosPulse: MVP Plan (Week 1)

## What Week 1 has to prove

That HosPulse can turn raw hospital financial data into a correct, plain-English "which hospital is in trouble and why" answer, end to end. Week 1 proves it with public CMS cost report data only (no customer data, no patient data) for Oklahoma and Texas rural hospitals, so there is something real to show prospect #1. Known limit: public cost reports lag 1 to 2 years, which is exactly the gap the paid monthly-upload product closes, and a good talking point.

## Build this, and only this

- [ ] **HCRIS Importer** (Python + DuckDB): download the latest 3 years of CMS HCRIS hospital cost report files, keep only rural and Critical Access Hospitals in Oklahoma and Texas, and extract the raw inputs for three metrics. Safe to re-run: same files in, same rows out.
- [ ] **Metrics Database** (PostgreSQL on Supabase, free tier): one `hospitals` table and one `yearly_metrics` table (hospital, year, operating margin, days cash on hand, days in A/R). Load is an upsert (update if present, insert if not) so re-imports never duplicate rows.
- [ ] **KPI + Early-Warning Engine** (Python, rules tested with pytest): exactly three rules: operating margin below 0%, days cash on hand below 30, days in A/R rising two years in a row. Each flag stores the numbers that triggered it.
- [ ] **Public Health Snapshot Page** (Next.js, run locally): a search box, plus one hospital page showing the three metrics, a 3-year trend line, and any flags in plain words.
- [ ] **AI Briefing Agent** (Claude Sonnet 5, run by hand from a script): given a list of 5 to 10 hospitals, write a one-page "hospitals at risk" briefing using only the engine's stored numbers; the script fails if the briefing contains a number not present in the input.

## Explicitly not this week

- Operator Portal and Access Control: no customer data yet, so nothing needs logging in.
- Upload Intake + PHI Guard, Export File Storage, Normalizer: only needed once a management company sends its own monthly exports (after the CEO conversation).
- Scheduler (GitHub Actions): public data changes quarterly; running the importer and briefing by hand is fine for now.
- Email Delivery Service (Resend): the Week 1 briefing is handed over in person, not emailed.
- Cost Report Co-pilot: Phase 3; needs customer ledger data and a reimbursement expert to check findings.
- Public deploy to Vercel: run locally until the numbers have been checked against a few published hospital financials.
- More than three warning rules: three correct rules prove the idea better than ten unchecked ones.

## How you'll know it worked

You can open the Snapshot page on your laptop, look up any Oklahoma rural hospital, and see three years of margin, cash and A/R with correct flags. Then you run one command that produces a one-page briefing for a chosen list of hospitals, where every number in it matches the database, and it is good enough to put in front of prospect #1.

## Grounded in

- Architecture: `project-blueprint/architecture.md` (HCRIS Importer, Metrics Database, KPI + Early-Warning Engine, Public Health Snapshot Page, AI Briefing Agent)
- Tech stack: `project-blueprint/tech-stack.md` (Python + DuckDB, Supabase PostgreSQL, Python + pytest, Next.js, Claude Sonnet 5)
