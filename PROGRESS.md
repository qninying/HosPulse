# PROGRESS

## Setup

- [x] Create project folder, README, CLAUDE.md, prospect list
  - Date: 2026-09-22
  - What changed: initial repo scaffold; `docs/research/rural_hospital_mgmt_companies.csv` (10 prospects, ranked)
  - Verification: files present, private GitHub repo created

- [x] Blueprint: architecture, tech stack, MVP plan, mockup, one-pager
  - Date: 2026-09-22
  - What changed: `project-blueprint/` (architecture.md, tech-stack.md, mvp-plan.md, mockup.html, one-pager.html/.pdf, colaberry-idea-prompt.md)
  - Verification: one-pager rendered to a real 1-page PDF with headless Chrome; mockup screenshot checked

- [x] Plan and Command Center (CoreOps structure)
  - Date: 2026-09-22
  - What changed: `.hospulse/plan.json` (19 requirements, 12 stories, 5 releases, 2 agents); `scripts/build_plan.py` generates docs, progress and manifest; `docs/` REQUIREMENTS, STORIES, TRACEABILITY, DATA_CONTRACT, stories/STORY-000..012; `command-center/` 9 tabs
  - Verification: `python3 -m unittest discover scripts` 6 tests OK; second build run prints "no changes"; 17 pages x 2 modes rendered in the browser with no console errors
  - Notes: STORY-000 has 3 of 5 criteria passed; the 2 that require `.hospulse/` to be committed stay false until the first commit. Preview launcher cannot read ~/Desktop (macOS permission), so verification used a temporary `python3 -m http.server`.

- [x] Make repo public and connect to the Colaberry platform
  - Date: 2026-09-22
  - What changed: squashed git history to a single commit (removed a prospect's name that appeared in the original first commit), repo set to public, `.colaberry/connect.txt` committed, push webhook to enterprise.colaberry.ai registered, `.colaberry/progress.json` (platform-generated, 14 stories) added
  - Verification: fetched and text-searched the actual GitHub history post-push, zero matches for the prospect's name; `gh api .../hooks` confirms the webhook is registered and active

- [x] Grounding guardrail: reject any AI output with an unsupported dollar/percent/days figure
  - Date: 2026-09-22
  - What changed: `pipeline/grounding_guardrail.py` (`validate_ai_output_is_grounded`, shared by the briefing agent and the cost report co-pilot), `pipeline/test_grounding_guardrail.py`; added a concrete acceptance criterion to STORY-011 naming this module, replacing prose-only coverage; regenerated `docs/stories/STORY-011.md`
  - Verification: `.venv/bin/python -m pytest pipeline/ -v` 16/16 passed; `python3 scripts/build_plan.py` run twice, second run "no changes"; `python3 -m unittest discover scripts` 6/6 passed

- [x] Repoint Command Center at the Colaberry platform's own plan (STORY-000, platform-side)
  - Date: 2026-09-22
  - What changed: root `index.html` redirect to `command-center/index.html` (GitHub Pages entry point requirement); `command-center/assets/command-center.js` DATA_DIR switched from `.hospulse` to `.colaberry`; added `CommandCenter.ownersFromPlan()` fallback since this plan has no `derived.owners`; `command-center/agents.html` updated to use it; `plan.schedule` null-guarded in `init()`; `.colaberry/plan.json` and `manifest.json` added (plan.json's `schedule`/release/story dates backfilled from the portal's STORY-000 text, since the generated seed had `schedule: null`); `.colaberry/progress.json` STORY-000 criteria ticked (5/5) with evidence in `notes`; `.colaberry/enrichment/STORY-000.json` written; `docs/stories/STORY-000.md` replaced with the platform's current version; `CLAUDE.md` documents the `.colaberry` (Command Center, platform-owned) vs `.hospulse` (private build plan) split; GitHub Pages turned on (`https://qninying.github.io/HosPulse/`)
  - Verification: `node --check` clean on all JS (shared file + every inline script block); every `plan.X`/`progress.X` field referenced in the codebase traced against the real committed JSON; `ownersFromPlan`/`verificationForRequirement` run in Node against the real data, output matched the portal's hand-specified owner breakdown exactly; all 9 tabs + root redirect + 3 data files returned HTTP 200 from a local server
  - Notes: no live browser available this session to visually confirm rendering; verification was static (syntax, field trace, logic replay), not an observed render. `.hospulse/plan.json` and its generated `docs/` remain as a separate, still-valid build plan; the Command Center no longer reads them.

- [x] STORY-001: import CMS HCRIS data into real Supabase Postgres
  - Date: 2026-09-22
  - What changed: Supabase project created (`hospulse`, us-east-2), automatic-RLS-on-new-tables event trigger enabled; `pipeline/schema.sql` (`hospitals`, `cost_report_years`, generated `operating_margin_pct`/`days_cash_on_hand`/`days_in_ar` columns, public-read RLS policies); `pipeline/hcris_import.py` (downloads the real CMS HCRIS zip, filters to OK/TX rural and Critical Access Hospitals, computes the 3 metrics, idempotent upsert); `pipeline/test_hcris_import.py` (12 tests); `requirements.txt` (psycopg2-binary, duckdb, python-dotenv); `.colaberry/enrichment/STORY-001.json`
  - Verification: real run against live Supabase -- 256 OK/TX rural/CAH hospitals, 260 cost-report-years for FY2024; re-run from a clean state produced an identical content hash (genuine idempotency, not just "no crash"); `pytest pipeline/test_hcris_import.py -v` 12/12 passed, including the invalid-format failure path; every worksheet/line/column code confirmed against a real downloaded report (RPT_REC_NUM 795252) before being trusted, not taken from documentation alone
  - Notes: two real bugs found and fixed while verifying, not left in: (1) DuckDB lazy-evaluation bug -- reusing one registered view name ("kv") for two sequential pivots caused the first to silently read the second file's data, returning 0 results with no error; fixed by materializing into real temp tables. (2) Fiscal-year mislabeling -- CMS's HOSP10FY2024.ZIP bundles reports by when CMS processed them, not each report's own period end, so a report ending 06/30/2025 was being stored as fiscal_year=2024; fixed by deriving fiscal_year from the report's own fy_end_dt, plus a deterministic dedup tie-break for genuine same-year duplicates (highest RPT_REC_NUM wins). `.colaberry/progress.json` STORY-001 ticked 3/3 (genuinely earned). `.hospulse/progress.json` STORY-001 ticked honestly at 1/4 against its own stricter criteria -- only FY2024 imported (not 3 years), no explicit "reason" column for missing values, worksheet/line provenance lives in code not per-row in the database. Both are real, neither rounded up.

- [x] Expand HCRIS import to FY2025 and FY2023 (latest 3 years complete)
  - Date: 2026-09-22
  - What changed: `pipeline/hcris_import.py` -- added a WHERE guard to the `cost_report_years` upsert (`EXCLUDED.source_rpt_rec_num >= cost_report_years.source_rpt_rec_num`) so an older file re-run after a newer one can never regress a row back to a worse report; ran the importer for FY2025 then FY2023
  - Verification: live-tested the regression guard directly against Supabase (a same-key upsert with a lower record number was blocked, a higher one applied, then reverted to the real value); full pipeline re-run three times, content hash identical on runs 2 and 3 (genuine idempotency); final state: 274 OK/TX rural/CAH hospitals, 652 cost-report-years across FY2023/2024/2025, zero duplicate keys, zero mislabeled fiscal years; `pytest pipeline/` 28/28 passed
  - Notes: `.hospulse/progress.json` STORY-001's "latest three years" criterion now genuinely true (2/4 total there); not every hospital has a row in all 3 years, which is a real reporting gap (closures, fiscal-year-end changes), not a bug -- forcing one would mean inventing data

## Next

- [x] Close STORY-001's two remaining gaps: per-metric provenance and a real "missing" reason
  - Date: 2026-09-22
  - What changed: `pipeline/schema.sql` -- `metric_provenance jsonb` column on `cost_report_years` (migration via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, safe against the existing production table); `pipeline/hcris_import.py` -- pivot now tracks whether each worksheet line was present at all (not just its parsed value), builds a per-row provenance dict (`{wksht_cd, line_num, clmn_num, status}` per metric, status = ok / not_reported / unparseable), and a new `_dedupe_by_provider()` fixes a real crash found while backfilling; `pipeline/test_hcris_import.py` (2 more tests, 30 total)
  - Verification: schema migration applied live; backfilled all 652 existing rows (0 left with empty provenance); confirmed 18 rows genuinely have `cash_on_hand: not_reported` (a real distinction, not lost as an ambiguous NULL); full 3-fiscal-year re-run produced an identical content hash including provenance (idempotent); `pytest pipeline/` 30/30 passed; `.hospulse/progress.json` STORY-001 now 4/4, genuinely
  - Notes: real bug found while backfilling, not left in -- `hospitals` (keyed on `provider_ccn` alone) crashed on FY2025 with Postgres's "ON CONFLICT DO UPDATE command cannot affect row a second time," because a single run's batch can legitimately contain one hospital across two real fiscal years (the same split-year pattern found earlier in STORY-001). Fixed with a second, hospitals-scoped dedupe preferring the most recent fiscal year.

## Next

- [ ] Coffee with prospect #1 (4 validation checks: pain, data access, budget owner, existing tools)
- [ ] STORY-002: early-warning flags on top of the imported metrics
- [ ] Health Snapshot v0 from public CMS HCRIS cost report data (OK + TX rural hospitals)
- [ ] LinkedIn Post 1 (RHTP / visibility problem)
- [ ] Build STORY-011 / STORY-003 for real and wire them to call `pipeline/grounding_guardrail.validate_ai_output_is_grounded`
