# CLAUDE.md

HosPulse: early-warning intelligence for rural hospital management companies. Founder: Quincy Nkwain Ninying (AI Systems Architect). Claude Code is the engineering team.

## Hard rules

- **No PHI.** Do not ingest, store, or log patient data. Public data (CMS HCRIS) and aggregate financial/operational data only, until BAAs and a HIPAA review exist. Any change that would touch PHI is an escalation, not an implementation decision.
- **No secrets in the repo.** Config and keys live in env vars; `.env` is gitignored.
- **Never commit or push unless explicitly asked** for that specific change.
- **No em dashes** in any document or content produced for this project.
- **No Claude/Anthropic attribution** on anything meant to be posted, shared, or sent to prospects.
- **Never name a prospect or contact publicly** (LinkedIn, public repos) without their permission.

## Where the truth lives

- `.hospulse/plan.json`: requirements, stories, releases, agents, dates. The only planning file you edit by hand.
- `docs/REQUIREMENTS.md`, `docs/STORIES.md`, `docs/TRACEABILITY.md`, `docs/stories/STORY-nnn.md`: generated from the plan. Never edit them directly.
- `docs/stories/STORY-000.md`: the Command Center brief, hand-written.
- `docs/DATA_CONTRACT.md`: the field-by-field spec of `.hospulse/*.json`. Read it before touching the Command Center.
- `project-blueprint/`: architecture, tech stack, MVP plan, mockup, one-pager.

After changing the plan or ticking criteria, run `python3 scripts/build_plan.py`. Tests: `python3 -m unittest discover scripts`.

Read the requirement before writing code for a story. If the requirement is wrong, fix it in the plan: you are the architect here, not a typist.

## Command Center

`command-center/` is a static 9-tab site that reads `.hospulse/*.json` at runtime. Serve the repo root over HTTP (`python3 -m http.server 8765`) and open `/command-center/`; opening from disk cannot fetch the JSON. Nothing in it may show a number, connection or result the project has not actually produced.

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
