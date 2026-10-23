import json
import unittest
from pathlib import Path

import fakes
from shared.checks import evaluate
from shared.measure import PARTS, loc_report

ROOT = Path(__file__).resolve().parent.parent

STATE = {
    "tasks": [{"id": "T1", "course": "Algorithms", "due": "2026-10-29", "status": "open"},
              {"id": "T2", "course": "Operating Systems", "due": "2026-10-28", "status": "done"}],
    "memory": [{"id": "M1", "fact": "I study at most 3 hours per day"}],
    "plan": {"hours_per_day": 3, "days": {"2026-10-25": ["T1 3h"], "2026-10-26": ["T1 3h"],
                                          "2026-10-31": []}},
}
TURNS = [{"session": "session2", "metrics": {"tools": ["list_tasks", "get_jewish_calendar"]}}]


def run(check, state=STATE):
    return evaluate([{"name": "c", **check}], {"s:1": state}, TURNS)[0]


class ChecksTest(unittest.TestCase):
    def test_passing_checks(self):
        cases = [
            {"type": "task_exists", "course": "algo", "due": "2026-10-29"},
            {"type": "task_status", "course": "Operating", "status": "done"},
            {"type": "task_count", "n": 2},
            {"type": "memory_contains", "words": ["3", "HOUR"]},
            {"type": "plan_hours_per_day", "value": 3},
            {"type": "plan_max_hours", "limit": 3},
            {"type": "plan_skips", "date": "2026-10-31"},
            {"type": "plan_excludes_task", "course": "Operating"},
            {"type": "tool_called", "tool": "get_jewish_calendar", "session": "session2"},
        ]
        for c in cases:
            self.assertTrue(run(c)["passed"], c)

    def test_failing_checks(self):
        bad = {"tasks": STATE["tasks"], "memory": [],
               "plan": {"hours_per_day": 6, "days": {"2026-10-26": ["T1 6h", "T2 1h"]}}}
        cases = [
            {"type": "memory_contains", "words": ["3", "hour"]},
            {"type": "plan_hours_per_day", "value": 3},
            {"type": "plan_max_hours", "limit": 3},
            {"type": "plan_excludes_task", "course": "Operating"},
            {"type": "tool_called", "tool": "plan_week", "session": "session2"},
            {"type": "task_exists", "course": "Calculus", "due": "2026-11-03"},
        ]
        for c in cases:
            self.assertFalse(run(c, bad)["passed"], c)

    def test_empty_plan_never_passes(self):
        empty = {"tasks": [], "memory": [], "plan": {}}
        for c in [{"type": "plan_skips", "date": "2026-10-31"}, {"type": "plan_max_hours", "limit": 3},
                  {"type": "plan_excludes_task", "course": "x"}]:
            self.assertFalse(run(c, empty)["passed"], c)

    def test_broken_check_is_a_fail_not_a_crash(self):
        res = run({"type": "task_count"})
        self.assertFalse(res["passed"])
        self.assertIn("failed to run", res["detail"])

    def test_scenario_file_is_valid(self):
        data = json.loads((ROOT / "scenario.json").read_text(encoding="utf-8"))
        n = sum(len(s["messages"]) for s in data["sessions"])
        self.assertTrue(6 <= n <= 8)
        self.assertEqual(len(data["sessions"]), 2)
        self.assertGreaterEqual(len(data["checks"]), 5)
        keys = {f"{s['name']}:{i}" for s in data["sessions"] for i in range(1, len(s["messages"]) + 1)}
        for c in data["checks"]:
            self.assertTrue(c.get("at", "end") in keys | {"end"}, c["name"])


class MeasureTest(unittest.TestCase):
    def test_loc_report(self):
        rep = loc_report()
        self.assertEqual(set(rep["api_harness"]), set(PARTS))
        self.assertTrue(all(n > 0 for n in rep["api_harness"].values()))
        sdk = rep["sdk_replacement"]
        for part in PARTS:
            self.assertGreater(sdk[part], 0, part)
        self.assertGreater(sum(rep["api_harness"].values()), sum(sdk.values()))


if __name__ == "__main__":
    unittest.main()
