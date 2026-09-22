# Colaberry idea prompt

**Name:** HosPulse

**What do you want to build?** (paste everything below)

---

HosPulse is early-warning intelligence for companies that manage rural and Critical Access Hospitals. These management companies run several small hospitals at once, often court-appointed turnarounds, each on a different mix of billing and accounting systems. Today they find out a hospital is slipping weeks late, from monthly reports built by hand. HosPulse gives them one view across every hospital they manage and a plain-English briefing every Monday telling them which hospitals need attention, why, and where to look first.

Who uses it: the CEO, COO and CFO of a rural hospital management company (the buyer and daily user), hospital CEOs (who see the free public snapshot), and reimbursement specialists (who review cost report findings). The first customer is a rural hospital management company in Oklahoma that I have a personal relationship with.

What it must do well on day one: take hospital financial data and produce a correct, traceable "which hospital is in trouble and why" answer, where every number can be traced back to the exact source line it came from and the AI never invents a figure.

How it works, in phases:

1. Free public Health Snapshot. Import the public CMS HCRIS Medicare cost report files for rural and Critical Access Hospitals in Oklahoma and Texas. Compute operating margin, days cash on hand and days in A/R per hospital per year. Anyone can search a hospital and see three years of trends, with the data year shown next to every figure and a note that public data lags one to two years. This is also the sales demo and LinkedIn content.
2. Early-warning engine. Fixed, tested rules (not AI) flag hospitals: operating margin below 0%, days cash on hand below 30, days in A/R rising two years in a row. Every flag stores the exact values that triggered it. Missing data is marked "not assessable", never treated as healthy or zero.
3. AI briefing agent. Claude writes a one-page hospitals-at-risk briefing from the engine's output only. A grounding check extracts every number in the briefing and rejects it if any number is not in the input. Capped retries on API failure, nothing partial saved.
4. Private operator portal. Operators sign in, and each management company only ever sees its own hospitals, enforced by database row-level security. They upload monthly exports per hospital: general ledger, A/R aging, denials summary, staffing. A patient-data guard rejects any file containing patient names, birth dates or record numbers before it is stored or logged. Duplicate uploads are detected by file hash.
5. Normalizer. Converts exports from different hospital systems into one standard set of monthly metrics (cash, days in A/R, denial rate, open positions). Unknown formats are marked "needs mapping" rather than guessed. Every metric links back to the file and row it came from.
6. Dashboard and weekly email. Every managed hospital with status, days cash, days in A/R, margin and a 12-week trend. Status colors come only from engine flags. The briefing is emailed every Monday 6:00 AM Central, once per company per week even if the job runs twice.
7. Cost report co-pilot (later). Compares a hospital's cost report with its ledger totals and lists possible missed reimbursement, each citing the lines it compared. Every finding stays "unconfirmed" until a human reimbursement specialist confirms or rejects it, recorded in an append-only audit log.

Guardrails that must never break:
- No patient data (PHI), ever, until BAAs and a HIPAA review exist. Financial and operational totals only.
- No company can see another company's hospitals.
- The AI never produces a number that is not in the computed data.
- Every number is traceable to its source.
- Every import, upload, normalization and email is idempotent: running it twice changes nothing.
- AI findings on reimbursement are suggestions until a human confirms them.

Data it touches: public CMS HCRIS cost reports; customer monthly financial and operational exports (CSV or Excel, no patient data); computed metrics, flags, briefings and audit records.

Systems it must work with: CMS HCRIS public files, Supabase (auth, Postgres, storage), Vercel, the Anthropic Claude API, Resend for email. Python for data work, Next.js for the web app. Running cost under $200 a month until 10 paying customers.

What "done" looks like: an operator uploads a month of exports for two hospitals on different systems and gets a Monday briefing that correctly flags the one that is slipping, at least 4 weeks earlier than their current monthly reporting would have, with every number traceable.

What I have always wished existed: one screen that tells a rural hospital operator, before the board meeting, which hospital is quietly running out of cash, in plain words.
