import unittest

import fakes
from shared.report import results_table, turns_table

SDK = {"totals": {"input": 10, "cache_read": 900, "cache_write": 90, "output": 50, "cache_hit_pct": 90.9,
                  "calls": 3, "cost_usd": 0.01234, "seconds": 4.25}, "passed": "9/9"}


class ReportTest(unittest.TestCase):
    def test_missing_turns_show_dash(self):
        self.assertEqual(turns_table(None), "—")

    def test_missing_version_shows_dash(self):
        table = results_table(None, SDK)
        self.assertIn("| cost (USD) | — | $0.0123 |", table)
        self.assertIn("| checks passed | — | 9/9 |", table)


if __name__ == "__main__":
    unittest.main()
