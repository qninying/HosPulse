# CLAUDE.md

HosPulse: early-warning intelligence for rural hospital management companies. Founder: Quincy Nkwain Ninying (AI Systems Architect). Claude Code is the engineering team.

## Hard rules

- **No PHI.** Do not ingest, store, or log patient data. Public data (CMS HCRIS) and aggregate financial/operational data only, until BAAs and a HIPAA review exist. Any change that would touch PHI is an escalation, not an implementation decision.
- **No secrets in the repo.** Config and keys live in env vars; `.env` is gitignored.
- **Never commit or push unless explicitly asked** for that specific change.
- **No em dashes** in any document or content produced for this project.
- **No Claude/Anthropic attribution** on anything meant to be posted, shared, or sent to prospects.
- **Never name a prospect or contact publicly** (LinkedIn, public repos) without their permission.

## Two plans, on purpose, not a duplication to clean up

There are two separate `plan.json`s in this repo, owned by different things:

- **`.colaberry/`** (`plan.json`, `progress.json`, `manifest.json`): owned by the Colaberry platform, refreshed on every portal sync. **This is what `command-center/` reads at runtime.** Verification, points, and what the portal shows all come from here. Don't hand-edit `plan.json` or `manifest.json`; the platform overwrites them. `progress.json`'s `criteria[].passed`, `files_touched`, `tests_added` and `notes` are yours to set per story; `verification` is the platform's.
- **`.hospulse/`** (`plan.json`, generated `docs/`, `scripts/build_plan.py`): a separate, hand-maintained build plan for the actual engineering work (importer, engine, briefing agent, etc.), independent of what Colaberry tracks. It is not read by the Command Center. Keep using it for real implementation planning; after changing it, run `python3 scripts/build_plan.py` (tests: `python3 -m unittest discover scripts`).

`docs/DATA_CONTRACT.md` is the field-by-field spec for both `plan.json` shapes (same schema). `docs/stories/STORY-000.md` is the Colaberry-generated Command Center brief; when it's superseded by a fresher portal version, overwrite it, it isn't hand-authored content to protect. `project-blueprint/`: architecture, tech stack, MVP plan, mockup, one-pager, plus `hospulse-docs-backup/`, a snapshot of the `.hospulse/`-generated docs taken before Colaberry's sync started overwriting `docs/`.

Read the requirement before writing code for a story, in whichever plan owns it. If a requirement is wrong, fix it in that plan: you are the architect here, not a typist.

## Command Center

`command-center/` is a static 9-tab site. Entry point is `index.html` at the repo root (a redirect to `command-center/index.html`, per Colaberry's GitHub Pages convention). It reads `.colaberry/plan.json`, `progress.json` and `manifest.json` at runtime — serve the repo root over HTTP (`python3 -m http.server 8765`) and open `/command-center/`; opening from disk cannot fetch the JSON. `plan.derived.owners` may be absent (this platform's generator doesn't precompute it); `CommandCenter.ownersFromPlan()` derives it from `stories[].owner_agent` when missing, don't reintroduce a direct `plan.derived.owners` read. Nothing in it may show a number, connection or result the project has not actually produced.

## When you finish a story

1. In `.hospulse/progress.json`, set `passed` on each criterion that genuinely passes, and fill `files_touched` and `tests_added`. Never add or reword criteria there.
2. Run `python3 scripts/build_plan.py`.
3. When asked to commit, name the story in a trailer: `Story: STORY-nnn` on its own line. A story only shows as verified when every criterion passes **and** such a commit exists.
4. Add a `PROGRESS.md` entry.

## How we work

- Proceed on reversible, local implementation decisions. Escalate on data/compliance, paid services, and architecture shifts.
- Every data pipeline must be idempotent and safe to re-run.
- Tests land with the code they cover.
- Log completed changes in `PROGRESS.md` with date and verification evidence.
