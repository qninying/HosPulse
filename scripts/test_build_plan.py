"""Tests for scripts/build_plan.py. Run: python3 -m unittest discover scripts"""

import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_plan  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


class DerivedTests(unittest.TestCase):
    def setUp(self):
        self.plan = {
            "requirements": [
                {"id": "REQ-1", "kind": "SAFE", "priority": "must", "statement": "s1", "fulfilled_by": ["STORY-1"]},
                {"id": "REQ-2", "kind": "NFR", "priority": "should", "statement": "s2", "fulfilled_by": []},
                {"id": "REQ-3", "kind": "CONSTRAINT", "priority": "must", "statement": "s3",
                 "systems": ["Supabase", "Resend"], "fulfilled_by": ["STORY-1"]},
            ],
            "releases": [{"key": "r0"}, {"key": "r1"}],
            "stories": [
                {"id": "STORY-1", "release": "r0", "narrative": "As an Operator, I want x, so that y.",
                 "owner_agent": "Portal", "failure_paths": ["a", "b"], "blocked_by": []},
                {"id": "STORY-2", "release": "r0", "narrative": "As a CFO, I want x, so that y.",
                 "owner_agent": "Portal", "failure_paths": ["c"], "blocked_by": ["STORY-1"]},
            ],
            "agents": [],
        }

    def test_roles_owners_systems_and_counts(self):
        d = build_plan.compute_derived(self.plan)
        self.assertEqual(d["roles"], ["Operator", "CFO"])
        self.assertEqual(d["owners"], [{"name": "Portal", "owns": ["STORY-1", "STORY-2"]}])
        self.assertEqual(d["systems"], ["Supabase", "Resend"])
        self.assertEqual([g["id"] for g in d["guardrails"]], ["REQ-1"])
        self.assertEqual([m["id"] for m in d["measures"]], ["REQ-2"])
        self.assertEqual(d["counts"]["failure_paths_total"], 3)

    def test_check_plan_flags_must_gap_and_forward_dependency(self):
        self.plan["requirements"][0]["fulfilled_by"] = []
        self.plan["stories"][0]["release"] = "r1"  # STORY-2 (r0) now depends on a later release
        problems = build_plan.check_plan(self.plan)
        self.assertIn("REQ-1 is a must with no story", problems)
        self.assertIn("STORY-2 depends on later-release story STORY-1", problems)

    def test_role_of_ignores_malformed_narrative(self):
        self.assertIsNone(build_plan.role_of("I want things"))


class ProgressTests(unittest.TestCase):
    def test_ticks_survive_and_state_is_honest_without_commit(self):
        plan = {"project_name": "T", "project": {}, "stories": [
            {"id": "STORY-900", "release": "r0", "acceptance": ["a", "b"]}]}
        old = {"stories": [{"id": "STORY-900", "criteria": [{"text": "a", "passed": True}], "notes": "kept"}]}
        progress = build_plan.build_progress(plan, old)
        story = next(s for s in progress["stories"] if s["id"] == "STORY-900")
        self.assertEqual([c["passed"] for c in story["criteria"]], [True, False])
        self.assertEqual(story["notes"], "kept")
        self.assertEqual(story["verification"]["state"], "in_progress")
        self.assertEqual(story["verification"]["outstanding"], ["b"])

    def test_all_ticked_without_commit_is_submitted_not_verified(self):
        plan = {"project_name": "T", "project": {}, "stories": [
            {"id": "STORY-901", "release": "r0", "acceptance": ["a"]}]}
        old = {"stories": [{"id": "STORY-901", "criteria": [{"text": "a", "passed": True}]}]}
        story = next(s for s in build_plan.build_progress(plan, old)["stories"] if s["id"] == "STORY-901")
        self.assertEqual(story["verification"]["state"], "submitted")


class IdempotencyTest(unittest.TestCase):
    def test_second_run_changes_nothing(self):
        script = ROOT / "scripts" / "build_plan.py"
        subprocess.run([sys.executable, str(script)], check=True, capture_output=True, timeout=60)
        second = subprocess.run([sys.executable, str(script)], check=True, capture_output=True, text=True, timeout=60)
        self.assertIn("no changes", second.stdout)


if __name__ == "__main__":
    unittest.main()
