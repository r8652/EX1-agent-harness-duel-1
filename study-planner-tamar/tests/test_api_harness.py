import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from fakes import FakeClient, text, tool_call, usage
from API.agent import ApiAgent
from API.harness.caching import cached_system, conversation_cache
from API.harness.compaction import render
from API.harness.context import build_user_turn
from API.harness.history import History
from API.harness.memory import Memory
from API.harness.tokens import TurnMeter, cost_usd
from API.harness.tools import Dispatcher, compact, tool_definitions
from shared.planner import Planner

TODAY = date(2026, 10, 25)


def block(name, args, id_="toolu_1"):
    return SimpleNamespace(type="tool_use", name=name, input=args, id=id_)


class ToolsTest(unittest.TestCase):
    def setUp(self):
        self.planner = Planner(tempfile.mkdtemp(), TODAY)
        self.d = Dispatcher(self.planner)
        self.meter = TurnMeter("claude-opus-5-5")

    def test_success_result(self):
        res = self.d.run(block("add_task", {"course": "OS", "title": "Lab", "due": "2026-10-30"}), self.meter)
        self.assertEqual(res["tool_use_id"], "toolu_1")
        self.assertNotIn("is_error", res)
        self.assertEqual(json.loads(res["content"])["added"], "T1|OS|Lab|due 2026-10-30|2h|open")

    def test_errors_go_back_to_model(self):
        cases = [block("complete_task", {"task_id": "T7"}),
                 block("fly_away", {}),
                 block("add_task", {"course": "OS"})]
        for b in cases:
            res = self.d.run(b, self.meter)
            self.assertTrue(res["is_error"], b.name)
        self.assertEqual(self.meter.tools, ["complete_task", "fly_away", "add_task"])

    def test_compact_output(self):
        self.assertEqual(compact({"a": [1, 2]}), '{"a":[1,2]}')
        self.assertTrue(compact({"x": "y" * 5000}).endswith("...(truncated)"))

    def test_definitions_are_stable_copies(self):
        defs = tool_definitions()
        defs[0]["name"] = "changed"
        self.assertEqual(tool_definitions()[0]["name"], "add_task")


class HistoryTest(unittest.TestCase):
    def test_append_only_and_resume(self):
        path = Path(tempfile.mkdtemp()) / "h" / "s.jsonl"
        h = History(path)
        h.append({"role": "user", "content": [{"type": "text", "text": "hi"}]})
        h.append({"role": "assistant", "content": [{"type": "text", "text": "hello"}]})
        before = path.read_text(encoding="utf-8")
        h.compact("they said hi")
        self.assertTrue(path.read_text(encoding="utf-8").startswith(before))
        self.assertEqual(h.messages, [])
        self.assertEqual(h.take_summary(), "they said hi")
        h.append({"role": "user", "content": [{"type": "text", "text": "again"}]})
        resumed = History(path)
        self.assertEqual(len(resumed.messages), 1)
        self.assertIsNone(resumed.take_summary())


class ContextMemoryTest(unittest.TestCase):
    def test_only_relevant_memory_enters_context(self):
        planner = Planner(tempfile.mkdtemp(), TODAY)
        planner.remember("I study at most 3 hours per day", ["hours"])
        planner.remember("My favourite course is Algorithms", ["course"])
        mem = Memory(planner.store)
        picked = mem.recall("plan my week, how many hours?")
        turn = build_user_turn("plan my week", planner, picked)
        ctx = turn["content"][0]["text"]
        self.assertIn("today: 2026-10-25 (Sunday)", ctx)
        self.assertIn("3 hours per day", ctx)
        self.assertNotIn("favourite", ctx)
        self.assertEqual(turn["content"][1]["text"], "plan my week")


class TokensCachingTest(unittest.TestCase):
    def test_cost_formula(self):
        u = {"input": 1_000_000, "cache_write": 1_000_000, "cache_read": 1_000_000, "output": 1_000_000}
        self.assertAlmostEqual(cost_usd("claude-opus-5-5", u), 4 + 5 + 0.2 + 20)

    def test_meter_sums_calls(self):
        m = TurnMeter("claude-opus-5-5")
        m.add(SimpleNamespace(**usage(100, 10, 900, 0)))
        m.add(SimpleNamespace(**usage(50, 20, 0, 950)))
        r = m.result()
        self.assertEqual((r["input"], r["cache_read"], r["cache_write"], r["output"], r["calls"]),
                         (150, 900, 950, 30, 2))
        self.assertEqual(r["cache_hit_pct"], 45.0)

    def test_breakpoints(self):
        self.assertEqual(cached_system("x")[0]["cache_control"], {"type": "ephemeral"})
        self.assertEqual(conversation_cache(), {"cache_control": {"type": "ephemeral"}})


class AgentLoopTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def test_parallel_tools_one_message_then_answer(self):
        client = FakeClient([
            tool_call(("add_task", {"course": "OS", "title": "Lab", "due": "2026-10-30", "hours": 3}),
                      ("remember", {"fact": "I study at most 3 hours per day"})),
            text("Done."),
        ])
        agent = ApiAgent(self.dir, "s1", TODAY, client=client)
        answer, metrics = agent.ask("Add OS lab, I study 3 hours a day")
        self.assertEqual(answer, "Done.")
        self.assertEqual(metrics["calls"], 2)
        self.assertEqual(metrics["tools"], ["add_task", "remember"])
        second = client.requests[1]["messages"]
        self.assertEqual([r["type"] for r in second[-1]["content"]], ["tool_result", "tool_result"])
        self.assertEqual(second[1]["content"][0]["type"], "thinking")
        self.assertEqual(len(agent.planner.store.tasks()), 1)
        self.assertEqual(len(agent.planner.store.memories()), 1)

    def test_request_settings(self):
        client = FakeClient([text("hi")])
        ApiAgent(self.dir, "s1", TODAY, client=client).ask("hello")
        req = client.requests[0]
        self.assertEqual(req["model"], "claude-opus-5-5")
        self.assertEqual(req["output_config"], {"effort": "medium"})
        self.assertEqual(req["thinking"], {"type": "adaptive"})
        self.assertEqual(req["cache_control"], {"type": "ephemeral"})
        self.assertEqual(len(req["tools"]), 6)

    def test_prefix_stays_identical_between_calls(self):
        client = FakeClient([tool_call(("list_tasks", {})), text("none"), text("ok")])
        agent = ApiAgent(self.dir, "s1", TODAY, client=client)
        agent.ask("what is open?")
        agent.ask("thanks")
        first, last = client.requests[0], client.requests[2]
        self.assertEqual(first["system"], last["system"])
        self.assertEqual(first["tools"], last["tools"])
        self.assertEqual(last["messages"][:len(first["messages"])], first["messages"])

    def test_compaction_replaces_history_with_summary(self):
        client = FakeClient([text("first", inp=6000), text("summary of talk"), text("second")])
        agent = ApiAgent(self.dir, "s1", TODAY, client=client, compact_at=5000)
        agent.ask("hello")
        answer, metrics = agent.ask("again")
        self.assertEqual(answer, "second")
        self.assertEqual(metrics["calls"], 2)
        self.assertNotIn("tools", client.requests[1])
        last = client.requests[2]["messages"]
        self.assertEqual(len(last), 1)
        self.assertIn("summary of talk", last[0]["content"][0]["text"])

    def test_session_two_sees_memory_from_disk(self):
        ApiAgent(self.dir, "s1", TODAY, client=FakeClient([
            tool_call(("remember", {"fact": "I study at most 3 hours per day", "tags": ["hours"]})),
            text("saved")])).ask("remember: 3 hours a day")
        client = FakeClient([text("3 hours")])
        ApiAgent(self.dir, "s2", TODAY, client=client).ask("how many hours a day do I study?")
        msgs = client.requests[0]["messages"]
        self.assertEqual(len(msgs), 1)
        self.assertIn("3 hours per day", msgs[0]["content"][0]["text"])

    def test_refusal_and_step_limit(self):
        refusal = text("")
        refusal.stop_reason = "refusal"
        agent = ApiAgent(self.dir, "s1", TODAY, client=FakeClient([refusal]))
        self.assertEqual(agent.ask("x")[0], "The request was declined.")
        loop = FakeClient([tool_call(("list_tasks", {})) for _ in range(15)])
        answer, metrics = ApiAgent(self.dir, "s2", TODAY, client=loop).ask("loop")
        self.assertEqual(metrics["calls"], 15)
        self.assertIn("too many steps", answer)

    def test_render_for_summary(self):
        msgs = [{"role": "user", "content": [{"type": "text", "text": "add lab"}]},
                {"role": "assistant", "content": [{"type": "thinking", "thinking": ""},
                                                  {"type": "tool_use", "name": "add_task", "input": {"a": 1}}]},
                {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]}]
        self.assertEqual(render(msgs), 'user: add lab\ntool call add_task {"a": 1}\ntool result: ok')


if __name__ == "__main__":
    unittest.main()
