# STORY-000: Build the Command Center

As a HosPulse Founder, I want one place that shows what we are building and how far along it is, so that I can see the whole project and demo from it.

**Release:** ahead of the plan, built on day one before any system story
**Owner:** the founder, with Claude Code
**Blocked by:** nothing

This file is hand-written. `scripts/build_plan.py` never regenerates it, but it reads the **Done means** lines below into `.hospulse/progress.json`.

## The requirement this satisfies

None, on purpose. The Command Center is the window onto the system, not part of it, so it fulfils no requirement in `docs/REQUIREMENTS.md` and has no row in `docs/TRACEABILITY.md`.

## Where the data comes from

The Command Center is static. It reads three files at runtime and never hard-codes their content:

- `.hospulse/plan.json`: the plan. Requirements, stories, releases, agents, dates. Hand-edited, then `derived` is recomputed by the script.
- `.hospulse/progress.json`: what is actually done. Criterion ticks, files touched, and each story's `verification.state`.
- `.hospulse/manifest.json`: `generated_at`, the time the data last changed.

See `docs/DATA_CONTRACT.md` for the field-by-field spec.

## Tabs

Nine tabs, each a real page under `command-center/`, and every card drills down one level:

1. **Overview**: name, descriptor, current release, headline counts from `progress.totals`.
2. **Outcomes**: the NFR measures from `plan.derived.measures`. Real mode says "not measured yet" until the running system measures them.
3. **Users and use case**: roles from `plan.derived.roles`, with the narratives they came from.
4. **Guardrails**: SAFE requirements and whether their stories are verified.
5. **Systems**: names from `plan.derived.systems`. Real mode shows every indicator grey, "not checked from here".
6. **Project management**: Gantt of releases, every story with baseline and current due dates, plus validation (prep) tasks.
7. **AI agents**: `plan.agents`, the design only. Real mode shows "no runs recorded".
8. **Knowledge base**: requirement traceability and a search panel over the plan.
9. **Data model**: the proposed tables, derived from the requirements.

## Sample data and real data

One global switch on every tab. Sample fills the page with believable made-up data and labels it as sample everywhere it appears. Real shows only what the project has actually produced.

## Done means

- Given the Command Center, when it is opened, then every tab is reachable and every card drills down one level.
- Given sample mode, when any tab is shown, then the sample data is visibly labelled as sample.
- Given the Command Center, when any tab renders, then .hospulse/plan.json and .hospulse/progress.json are both committed in this repo and every tab reads its content from them at runtime rather than from hard-coded values.
- Given the Command Center, when any tab is shown, then .hospulse/manifest.json is committed in this repo and every tab shows how old that data is and warns when the age exceeds a week.
- Trust: no tab shows a number, a connection or a result the project has not actually produced.
