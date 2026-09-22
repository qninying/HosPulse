#!/usr/bin/env python3
"""Rebuild everything derived from .hospulse/plan.json.

This script plays the role the Colaberry platform played for CoreOps:

1. Recomputes plan.json's `derived` block (measures, guardrails, systems,
   roles, owners, counts).
2. Merges .hospulse/progress.json: keeps our `passed` ticks and notes,
   refreshes the criterion list from the plan, and computes each story's
   verification state from the ticks plus a commit carrying `Story: STORY-nnn`.
3. Regenerates docs/REQUIREMENTS.md, docs/STORIES.md, docs/TRACEABILITY.md
   and docs/stories/STORY-nnn.md (never STORY-000.md, which is hand-written).
4. Rewrites .hospulse/manifest.json, moving `generated_at` only when the
   content of a tracked file actually changed.

Idempotent: running it twice in a row changes nothing the second time.
Standard library only. Usage: python3 scripts/build_plan.py
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / ".hospulse"
DOCS = ROOT / "docs"
STORY_DIR = DOCS / "stories"
PLAN = DATA / "plan.json"
PROGRESS = DATA / "progress.json"
MANIFEST = DATA / "manifest.json"
STORY_000 = STORY_DIR / "STORY-000.md"

KIND_LABEL = {
    "FUNC": "Functional",
    "SAFE": "Safety",
    "REL": "Reliability",
    "NFR": "Measure",
    "OBS": "Observability",
    "CONSTRAINT": "Constraint",
}

GIT_TIMEOUT_SECONDS = 10


# ---------- io helpers ----------

def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_if_changed(path: Path, text: str) -> bool:
    """Write only when content differs, so mtimes and diffs stay quiet."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def dump_json(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------- derived block ----------

ROLE_RE = re.compile(r"^As an? (.+?), I want")


def role_of(narrative: str) -> str | None:
    match = ROLE_RE.match(narrative or "")
    return match.group(1) if match else None


def compute_derived(plan: dict) -> dict:
    reqs = plan.get("requirements", [])
    stories = plan.get("stories", [])
    agents = plan.get("agents", [])

    roles: list[str] = []
    for s in stories:
        r = role_of(s.get("narrative", ""))
        if r and r not in roles:
            roles.append(r)

    owners: list[dict] = []
    for s in stories:
        name = s.get("owner_agent")
        if not name:
            continue
        entry = next((o for o in owners if o["name"] == name), None)
        if entry is None:
            entry = {"name": name, "owns": []}
            owners.append(entry)
        entry["owns"].append(s["id"])

    systems: list[str] = []
    for r in reqs:
        if r.get("kind") == "CONSTRAINT":
            for name in r.get("systems", []):
                if name not in systems:
                    systems.append(name)

    by_kind: dict[str, int] = {}
    for r in reqs:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1

    by_autonomy: dict[str, int] = {}
    for a in agents:
        level = a.get("autonomy_level", "unspecified")
        by_autonomy[level] = by_autonomy.get(level, 0) + 1

    return {
        "measures": [{"id": r["id"], "statement": r["statement"]} for r in reqs if r["kind"] == "NFR"],
        "guardrails": [{"id": r["id"], "statement": r["statement"]} for r in reqs if r["kind"] == "SAFE"],
        "systems": systems,
        "roles": roles,
        "owners": owners,
        "counts": {
            "requirements_total": len(reqs),
            "requirements_by_kind": dict(sorted(by_kind.items())),
            "stories_total": len(stories),
            "releases_total": len(plan.get("releases", [])),
            "agents_total": len(agents),
            "failure_paths_total": sum(len(s.get("failure_paths", [])) for s in stories),
            "agents_by_autonomy": dict(sorted(by_autonomy.items())),
        },
    }


def check_plan(plan: dict) -> list[str]:
    """Plan-gate problems worth shouting about. Returned, not raised: gaps are reported honestly."""
    problems = []
    story_ids = {s["id"] for s in plan.get("stories", [])}
    release_order = {r["key"]: i for i, r in enumerate(plan.get("releases", []))}
    story_release = {s["id"]: s["release"] for s in plan.get("stories", [])}
    for r in plan.get("requirements", []):
        if r["priority"] == "must" and not r.get("fulfilled_by"):
            problems.append(f"{r['id']} is a must with no story")
        for sid in r.get("fulfilled_by", []):
            if sid not in story_ids:
                problems.append(f"{r['id']} names unknown story {sid}")
    for s in plan.get("stories", []):
        for dep in s.get("blocked_by", []):
            if dep not in story_ids:
                problems.append(f"{s['id']} is blocked by unknown story {dep}")
            elif release_order[story_release[dep]] > release_order[s["release"]]:
                problems.append(f"{s['id']} depends on later-release story {dep}")
    return problems


# ---------- progress ----------

def story_000_criteria() -> list[str]:
    """The 'Done means' bullet lines of the hand-written STORY-000.md."""
    if not STORY_000.exists():
        return []
    lines = STORY_000.read_text(encoding="utf-8").splitlines()
    out, inside = [], False
    for line in lines:
        if line.startswith("## "):
            inside = line.strip() == "## Done means"
            continue
        if inside and line.startswith("- "):
            out.append(line[2:].strip())
    return out


def find_story_commit(story_id: str) -> dict | None:
    """Most recent commit whose message has a `Story: STORY-nnn` trailer line."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H%x09%cI", f"--grep=^Story: {story_id}$"],
            cwd=ROOT, capture_output=True, text=True, timeout=GIT_TIMEOUT_SECONDS, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"warning: git lookup for {story_id} failed ({type(exc).__name__}); treating as uncommitted")
        return None
    line = result.stdout.strip()
    if result.returncode != 0 or not line:
        return None
    sha, when = line.split("\t")
    return {"sha": sha, "at": when}


def repo_commit_url(plan: dict, sha: str) -> str | None:
    url = (plan.get("project") or {}).get("repo_url")
    return f"{url}/commit/{sha}" if url else None


def build_progress(plan: dict, old: dict | None) -> dict:
    old_by_id = {s["id"]: s for s in (old or {}).get("stories", [])}
    entries = [("STORY-000", None, story_000_criteria())]
    entries += [(s["id"], s["release"], s["acceptance"]) for s in plan.get("stories", [])]

    stories_out = []
    for sid, release, criteria_text in entries:
        prev = old_by_id.get(sid, {})
        prev_criteria = {c["text"]: c for c in prev.get("criteria", [])}
        criteria = []
        for text in criteria_text:
            p = prev_criteria.get(text, {})
            c = {"text": text, "passed": bool(p.get("passed", False))}
            if p.get("evidence"):
                c["evidence"] = p["evidence"]
            criteria.append(c)

        passed = sum(1 for c in criteria if c["passed"])
        total = len(criteria)
        commit = find_story_commit(sid)
        if total and passed == total and commit:
            state = "verified"
        elif total and passed == total:
            state = "submitted"
        elif passed:
            state = "in_progress"
        else:
            state = "not_started"

        stories_out.append({
            "id": sid,
            "release": release,
            "acceptance_total": total,
            "criteria": criteria,
            "files_touched": prev.get("files_touched", []),
            "tests_added": prev.get("tests_added", []),
            "notes": prev.get("notes"),
            "updated_at": prev.get("updated_at"),
            "verification": {
                "state": state,
                "criteria_passed": passed,
                "criteria_total": total,
                "verified_at": commit["at"] if state == "verified" else None,
                "commit_sha": commit["sha"] if commit else None,
                "commit_url": repo_commit_url(plan, commit["sha"]) if commit else None,
                "commit_at": commit["at"] if commit else None,
                "points_awarded": None,
                "outstanding": [c["text"] for c in criteria if not c["passed"]],
            },
        })

    def count(state):
        return sum(1 for s in stories_out if s["verification"]["state"] == state)

    return {
        "schema_version": 2,
        "project": plan.get("project_name"),
        "totals": {
            "stories_total": len(stories_out),
            "stories_verified": count("verified"),
            "stories_submitted": count("submitted"),
            "stories_in_progress": count("in_progress"),
            "stories_not_started": count("not_started"),
            "criteria_total": sum(s["acceptance_total"] for s in stories_out),
            "criteria_passed": sum(s["verification"]["criteria_passed"] for s in stories_out),
            "points_awarded": 0,
        },
        "stories": stories_out,
    }


# ---------- docs ----------

def release_by_key(plan: dict) -> dict:
    return {r["key"]: r for r in plan.get("releases", [])}


def weeks(r: dict) -> str:
    if r["week_start"] == r["week_end"]:
        return f"week {r['week_start']}"
    return f"weeks {r['week_start']} to {r['week_end']}"


def render_requirements(plan: dict) -> str:
    name = plan["project_name"]
    out = [
        f"# {name}: Requirements", "",
        plan["descriptor"], "",
        "Generated from `.hospulse/plan.json` by `scripts/build_plan.py`. Edit the plan, not this file.", "",
        "| Kind | Meaning |", "|---|---|",
        "| Functional | something the system does |",
        "| Safety | a guardrail, with a check that enforces it |",
        "| Reliability | how it behaves when something fails |",
        "| Measure | a number the system has to move |",
        "| Constraint | a platform or data source we must use, context rather than a task |", "",
    ]
    clusters: list[str] = []
    for r in plan["requirements"]:
        if r["cluster"] not in clusters:
            clusters.append(r["cluster"])
    for cluster in clusters:
        out += [f"## {cluster}", ""]
        for r in (x for x in plan["requirements"] if x["cluster"] == cluster):
            out += [f"### {r['id']}: {KIND_LABEL.get(r['kind'], r['kind'])} · {r['priority']}", "", r["statement"], ""]
            fulfilled = ", ".join(r.get("fulfilled_by", []))
            if fulfilled:
                out += [f"Fulfilled by: {fulfilled}", ""]
            elif r["priority"] == "must":
                out += ["**Gap: no story fulfils this must requirement.**", ""]
            else:
                out += ["Fulfilled by: no story yet (a measure tracked over time, not a build task)", ""]
    return "\n".join(out)


def render_stories_index(plan: dict) -> str:
    name = plan["project_name"]
    stories = plan["stories"]
    releases = plan["releases"]
    out = [
        f"# {name}: Stories", "",
        f"{len(stories)} stories across {len(releases)} releases, walking skeleton first: the",
        "earliest release proves the thinnest end-to-end path including the trust guarantees,",
        "and later releases stack features on top of something already working.", "",
        "Generated from `.hospulse/plan.json` by `scripts/build_plan.py`. Edit the plan, not this file.", "",
        "## Before the releases: start here", "",
        "- **[STORY-000](stories/STORY-000.md)**: Build the Command Center", "",
    ]
    for r in releases:
        out += [
            f"## {r['key']} · {r['name']} ({weeks(r)}, {r['starts_on']} to {r['ends_on']})", "",
            f"**Goal:** {r['goal']}",
            f"**Done when you can show:** {r['demo']}", "",
        ]
        for sid in r["story_ids"]:
            s = next(x for x in stories if x["id"] == sid)
            waits = f" _(waits on {', '.join(s['blocked_by'])})_" if s.get("blocked_by") else ""
            out.append(f"- **[{sid}](stories/{sid}.md)**: {s['title']}{waits}")
        out.append("")
    return "\n".join(out)


def render_traceability(plan: dict) -> str:
    out = [
        f"# {plan['project_name']}: Traceability", "",
        "Every requirement and the stories that fulfil it. A `must` with no story is a gap;",
        "a measure may legitimately have none, because it is tracked, not built.", "",
        "| Requirement | Kind | Priority | Fulfilled by |", "|---|---|---|---|",
    ]
    for r in plan["requirements"]:
        fulfilled = ", ".join(r.get("fulfilled_by", [])) or ("**GAP**" if r["priority"] == "must" else "none")
        out.append(f"| {r['id']} | {KIND_LABEL.get(r['kind'], r['kind'])} | {r['priority']} | {fulfilled} |")
    out.append("")
    return "\n".join(out)


def render_story(plan: dict, s: dict, progress_story: dict | None) -> str:
    rel = release_by_key(plan)[s["release"]]
    reqs = {r["id"]: r for r in plan["requirements"]}
    ticks = {c["text"]: c["passed"] for c in (progress_story or {}).get("criteria", [])}
    blocked = ", ".join(s.get("blocked_by", [])) or "nothing, you can start this now"
    acceptance_plain = "\n".join(f"- {a}" for a in s["acceptance"])
    failures = "\n".join(f"- {f}" for f in s["failure_paths"])
    deps = ", ".join(s.get("blocked_by", [])) or "nothing (this story has no dependencies)"

    out = [
        f"# {s['id']}: {s['title']}", "",
        s["narrative"], "",
        f"**Release:** {rel['key']} · {rel['name']} ({weeks(rel)})",
        f"**Owner:** {s['owner_agent']}",
        f"**Blocked by:** {blocked}",
        f"**Due:** {s['due_on']} (baseline {s['due_baseline_on']})", "",
        "## The requirements this satisfies", "",
    ]
    for rid in s["fulfills"]:
        r = reqs[rid]
        out.append(f"- **{rid}** ({KIND_LABEL.get(r['kind'], r['kind'])}, {r['priority']}): {r['statement']}")
    out += [
        "", "## How to build it", "", s["task_guidance"], "",
        "## Failure paths you must handle", "", failures, "",
        "## Acceptance: your stop condition", "",
        "Ticks mirror `.hospulse/progress.json`, which is the source of truth. Set `passed` there,",
        "then run `python3 scripts/build_plan.py` to refresh this file.", "",
    ]
    for a in s["acceptance"]:
        out.append(f"- [{'x' if ticks.get(a) else ' '}] {a}")
    out += [
        "", "---", "",
        "## Build prompt", "",
        "Copy everything below this line into Claude Code to build this story.", "",
        "```",
        f"Implement {s['id']}: {s['title']}.", "",
        s["narrative"], "",
        f"Before writing any code, confirm {deps} is already built and working.",
        "If it isn't, stop and say so rather than building on top of something that doesn't exist yet.", "",
        "Build only what this story needs. Don't build ahead into another story's scope.", "",
        "Acceptance criteria. All of these must genuinely pass, not just the happy path:",
        acceptance_plain, "",
        "Handle these failure paths explicitly; none may surface as an unhandled exception or a silent no-op:",
        failures, "",
        s["task_guidance"], "",
        "When you believe the story is done:",
        "1. Tests cover the happy path and at least one failure path above.",
        "2. Re-check every criterion against what the code actually does.",
        "3. No secrets or patient data in code, commits, or logs. Every side effect is idempotent.",
        f"4. In .hospulse/progress.json set `passed` on each criterion of {s['id']} that is truly met, fill",
        "   files_touched and tests_added, then run `python3 scripts/build_plan.py`.",
        f"5. Commit with `Story: {s['id']}` on its own line in the message, and add a PROGRESS.md entry.",
        "```", "",
    ]
    return "\n".join(out)


# ---------- manifest ----------

def tracked_files(plan: dict) -> list[Path]:
    files = [PLAN, PROGRESS, DOCS / "REQUIREMENTS.md", DOCS / "STORIES.md", DOCS / "TRACEABILITY.md", STORY_000]
    files += [STORY_DIR / f"{s['id']}.md" for s in plan["stories"]]
    return [f for f in files if f.exists()]


def build_manifest(plan: dict, old: dict | None) -> dict:
    files = [{"path": str(f.relative_to(ROOT)), "sha256": sha256(f)} for f in tracked_files(plan)]
    unchanged = old is not None and old.get("files") == files and old.get("generated_at")
    generated_at = old["generated_at"] if unchanged else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"generated_at": generated_at, "plan_version": plan["project"].get("plan_version"), "files": files}


# ---------- main ----------

def main() -> int:
    plan = read_json(PLAN)
    if plan is None:
        print(f"error: {PLAN} not found")
        return 1

    plan["derived"] = compute_derived(plan)
    changed = []
    if write_if_changed(PLAN, dump_json(plan)):
        changed.append(PLAN)

    progress = build_progress(plan, read_json(PROGRESS))
    if write_if_changed(PROGRESS, dump_json(progress)):
        changed.append(PROGRESS)
    progress_by_id = {s["id"]: s for s in progress["stories"]}

    outputs = {
        DOCS / "REQUIREMENTS.md": render_requirements(plan),
        DOCS / "STORIES.md": render_stories_index(plan),
        DOCS / "TRACEABILITY.md": render_traceability(plan),
    }
    for s in plan["stories"]:
        outputs[STORY_DIR / f"{s['id']}.md"] = render_story(plan, s, progress_by_id.get(s["id"]))
    for path, text in outputs.items():
        if write_if_changed(path, text):
            changed.append(path)

    manifest = build_manifest(plan, read_json(MANIFEST))
    if write_if_changed(MANIFEST, dump_json(manifest)):
        changed.append(MANIFEST)

    for problem in check_plan(plan):
        print(f"plan gap: {problem}")
    if changed:
        print("updated: " + ", ".join(str(p.relative_to(ROOT)) for p in changed))
    else:
        print("no changes")
    t = progress["totals"]
    print(f"stories verified {t['stories_verified']}/{t['stories_total']}, criteria passed {t['criteria_passed']}/{t['criteria_total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
