import tempfile
import unittest
from datetime import date

from fakes import hebcal_opener
from shared.planner import Planner, ToolError, relevant_memories
from shared.tool_specs import TOOL_METHODS, TOOL_SPECS, run_tool

TODAY = date(2026, 12, 1)
CHANUKAH = [{"date": "2026-12-05", "title": "Chanukah: 2 Candles"}]
PESACH = [{"date": "2026-12-03", "title": "Pesach I", "yomtov": True}]


class PlannerTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.p = Planner(self.dir, TODAY, hebcal_opener(CHANUKAH))

    def test_add_and_list_sorted_by_due(self):
        self.p.add_task("Algorithms", "HW3", "2026-12-08", 6)
        self.p.add_task("OS", "Lab 2", "2026-12-04", 3)
        res = self.p.list_tasks()
        self.assertEqual(res["count"], 2)
        self.assertTrue(res["tasks"][0].startswith("T2|OS|Lab 2|due 2026-12-04|3h"))

    def test_add_rejects_bad_input(self):
        with self.assertRaises(ToolError):
            self.p.add_task("OS", "Lab", "2026-11-01")
        with self.assertRaises(ToolError):
            self.p.add_task("OS", "Lab", "next week")
        with self.assertRaises(ToolError):
            self.p.add_task("OS", "Lab", "2026-12-10", -2)
        self.p.add_task("OS", "Lab", "2026-12-10")
        with self.assertRaises(ToolError):
            self.p.add_task("os", "lab", "2026-12-11")

    def test_list_filters_and_limit(self):
        for i in range(10):
            self.p.add_task("Calculus", f"Ex {i}", f"2026-12-{10 + i}", 1)
        self.p.add_task("OS", "Lab", "2026-12-02", 1)
        self.assertEqual(self.p.list_tasks(course="os")["count"], 1)
        self.assertEqual(self.p.list_tasks(days=1)["count"], 1)
        res = self.p.list_tasks()
        self.assertEqual(len(res["tasks"]), 8)
        self.assertEqual(res["more"], 3)

    def test_complete_task(self):
        self.p.add_task("OS", "Lab", "2026-12-10")
        self.p.complete_task("t1")
        self.assertEqual(self.p.store.tasks()[0]["status"], "done")
        self.assertEqual(self.p.list_tasks()["count"], 0)
        self.assertEqual(self.p.list_tasks(status="done")["count"], 1)
        with self.assertRaises(ToolError):
            self.p.complete_task("T1")
        with self.assertRaises(ToolError):
            self.p.complete_task("T9")

    def test_calendar_blocks_shabbat_and_yom_tov_only(self):
        p = Planner(self.dir, TODAY, hebcal_opener(CHANUKAH + PESACH))
        res = p.jewish_calendar("2026-12-01", "2026-12-07")
        self.assertEqual(res["blocked"], ["2026-12-03", "2026-12-05"])
        self.assertIn("2026-12-05 Chanukah: 2 Candles", res["events"])

    def test_calendar_errors(self):
        p = Planner(self.dir, TODAY, hebcal_opener(fail=True))
        with self.assertRaises(ToolError):
            p.jewish_calendar("2026-12-01", "2026-12-07")
        with self.assertRaises(ToolError):
            self.p.jewish_calendar("2026-12-07", "2026-12-01")
        with self.assertRaises(ToolError):
            self.p.jewish_calendar("2026-01-01", "2026-12-01")

    def test_plan_week_skips_shabbat_blocked_and_respects_hours(self):
        self.p.add_task("Algorithms", "HW3", "2026-12-08", 6)
        self.p.add_task("OS", "Lab 2", "2026-12-04", 3)
        res = self.p.plan_week("2026-12-03", 2, ["2026-12-04"])
        self.assertNotIn("2026-12-05", res["days"])
        self.assertNotIn("2026-12-04", res["days"])
        self.assertEqual(res["skipped"], ["2026-12-04", "2026-12-05"])
        self.assertEqual(res["days"]["2026-12-03"], ["T2 2h"])
        self.assertIn("T2 1h", res["unscheduled"])
        saved = self.p.store.plan()
        self.assertEqual(saved["hours_per_day"], 2)
        for items in saved["days"].values():
            self.assertLessEqual(sum(float(i.split()[1][:-1]) for i in items), 2)

    def test_plan_week_validation(self):
        with self.assertRaises(ToolError):
            self.p.plan_week(hours_per_day=0)
        with self.assertRaises(ToolError):
            self.p.plan_week(blocked=["tomorrow"])

    def test_remember_dedup_and_relevance(self):
        self.assertEqual(self.p.remember("I study at most 3 hours per day", ["hours"]), {"saved": "M1"})
        self.assertEqual(self.p.remember("i study at most 3 hours per day"), {"exists": "M1"})
        self.p.remember("Algorithms exam was moved to January", ["exam"])
        items = self.p.store.memories()
        self.assertEqual([m["id"] for m in relevant_memories(items, "How many hours a day?")], ["M1"])
        self.assertEqual(relevant_memories(items, "hello there"), [])
        with self.assertRaises(ToolError):
            self.p.remember("  ")

    def test_specs_match_methods(self):
        self.assertEqual({s["name"] for s in TOOL_SPECS}, set(TOOL_METHODS))
        for name, method in TOOL_METHODS.items():
            self.assertTrue(callable(getattr(self.p, method)), name)
        with self.assertRaises(KeyError):
            run_tool(self.p, "delete_everything", {})


if __name__ == "__main__":
    unittest.main()
