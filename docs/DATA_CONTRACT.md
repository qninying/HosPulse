# Data Contract: what is in `.hospulse/`

The Command Center reads three files. This is the field-by-field spec. It follows the same shape CoreOps used (schema version 2), with `scripts/build_plan.py` doing the job the Colaberry platform did there.

## The one rule

**`plan.json` is the plan. `progress.json` is the state.**

There is no `built` field on a requirement and no `status` field on a story. Completion lives in `progress.json` only, joined to the plan on story id.

## Who writes what

| File | Written by | You edit it? |
|---|---|---|
| `.hospulse/plan.json` | You, by hand. The script only recomputes the `derived` block. | Yes: requirements, stories, releases, agents, dates |
| `.hospulse/progress.json` | The script builds it; you own `passed`, `evidence`, `files_touched`, `tests_added`, `notes` | Only those fields |
| `.hospulse/manifest.json` | The script | Never |
| `docs/REQUIREMENTS.md`, `STORIES.md`, `TRACEABILITY.md`, `stories/STORY-001..` | The script, from the plan | Never (edit the plan) |
| `docs/stories/STORY-000.md` | You, by hand | Yes |

After any edit, run `python3 scripts/build_plan.py`. It is idempotent: a second run prints "no changes".

## `plan.json`

```
schema_version   2
project_name, descriptor

requirements[]   id, statement, kind (FUNC | SAFE | REL | NFR | OBS | CONSTRAINT),
                 priority (must | should), cluster, fulfilled_by[],
                 systems[] (CONSTRAINT only: names shown on the Systems tab)

releases[]       key (r0...), name, goal, demo, week_start, week_end, story_ids[],
                 starts_on, ends_on, is_demo_target

stories[]        id, release (a key), title, narrative ("As a <role>, I want ..."),
                 fulfills[], owner_agent, acceptance[] (exact criterion text),
                 task_guidance, failure_paths[], blocked_by[], due_on, due_baseline_on

agents[]         id, name, purpose, trigger_type, trigger, inputs[], outputs[],
                 autonomy_level, approval_gates[], escalation_rules[], skills[], owns[]

project          name, descriptor, repo_url, plan_version
schedule         build_start, build_end, demo_day, build_weeks, demo_release_key,
                 roadmap_release_keys[], prep[] { key, title, due_on }

derived          (computed, never hand-edited)
                 measures[]   NFR requirements
                 guardrails[] SAFE requirements
                 systems[]    from CONSTRAINT requirements' systems[]
                 roles[]      from story narratives
                 owners[]     { name, owns[] } from owner_agent
                 counts       totals
```

`due_baseline_on` is the first date a story was given and never moves. When a story slips, change only `due_on`; the Command Center shows the gap.

## `progress.json`

```
schema_version, project
totals           stories_total, stories_verified, stories_submitted, stories_in_progress,
                 stories_not_started, criteria_total, criteria_passed, points_awarded (always 0)
stories[]        id, release, acceptance_total, criteria[] { text, passed, evidence? },
                 files_touched[], tests_added[], notes, updated_at,
                 verification { state, criteria_passed, criteria_total, verified_at,
                                commit_sha, commit_url, commit_at, points_awarded, outstanding[] }
```

`verification.state` is computed by the script, never typed:

| State | Means |
|---|---|
| `not_started` | no criterion ticked |
| `in_progress` | some ticked |
| `submitted` | all ticked, but no commit with a `Story: STORY-nnn` trailer yet |
| `verified` | all ticked **and** a commit names the story |

Criteria are matched by exact text. Reword a criterion in the plan and its old tick is dropped, on purpose.

## `manifest.json`

`generated_at` plus a SHA-256 per tracked file. `generated_at` moves only when a tracked file's content changes, so "Data as of" means "the data last changed on", not "the script last ran on".

## What the Command Center cannot show

- **The value of any measure.** The plan holds the target, never the measurement.
- **Whether a system is connected.** `derived.systems` is a list of names.
- **Agent run history.** No agent has run until it is built.

Grey and "not checked from here" is the honest rendering. A confident zero is not.
