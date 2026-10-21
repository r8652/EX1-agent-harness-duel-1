import asyncio
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from fakes import FakeClient, text, tool_call
from API.agent import ApiAgent
from shared.runner import run_scenario

SCENARIO = {
    "today": "2026-10-25",
    "sessions": [
        {"name": "s1", "messages": ["add OS lab due 2026-10-30"]},
        {"name": "s2", "messages": ["what is open?"]},
    ],
}


class RunnerTest(unittest.TestCase):
    def test_runs_sessions_on_fresh_agents_from_clean_state(self):
        root = Path(tempfile.mkdtemp())
        scenario = root / "scenario.json"
        scenario.write_text(json.dumps(SCENARIO), encoding="utf-8")
        state = root / "state"
        state.mkdir()
        (state / "tasks.json").write_text('[{"id": "T9"}]', encoding="utf-8")
        client = FakeClient([
            tool_call(("add_task", {"course": "OS", "title": "Lab", "due": "2026-10-30"})),
            text("added"),
            tool_call(("list_tasks", {})),
            text("T1 is open"),
        ])
        created = []

        def make(state_dir, name, today):
            created.append(name)
            return ApiAgent(state_dir, name, today, client=client)

        with contextlib.redirect_stdout(io.StringIO()):
            result = asyncio.run(run_scenario("api", scenario, root / "out.json", state, make))
        self.assertEqual(created, ["s1", "s2"])
        self.assertEqual([t["reply"] for t in result["turns"]], ["added", "T1 is open"])
        self.assertEqual(json.loads((state / "tasks.json").read_text())[0]["id"], "T1")
        self.assertEqual(result["totals"]["calls"], 4)
        self.assertTrue((root / "out.json").exists())
        self.assertEqual(len(client.requests[2]["messages"]), 1)


if __name__ == "__main__":
    unittest.main()
