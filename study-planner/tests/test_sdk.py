import asyncio
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock

from fakes import hebcal_opener
import SDK.agent
from SDK.agent import SdkAgent, write_memory_file
from SDK.tools import TOOL_NAMES, build_server, make_handler
from shared.planner import Planner

TODAY = date(2026, 10, 25)


class FakeSdkClient:
    instances = []

    def __init__(self, options):
        self.options = options
        self.prompts = []
        self.closed = False
        self.cost = 0.0
        FakeSdkClient.instances.append(self)

    async def connect(self):
        pass

    async def query(self, prompt):
        self.prompts.append(prompt)

    async def receive_response(self):
        self.cost += 0.0123
        yield AssistantMessage(content=[ToolUseBlock("t1", "mcp__planner__list_tasks", {})],
                               model="claude-opus-5-5")
        yield AssistantMessage(content=[TextBlock("No open tasks.")], model="claude-opus-5-5")
        yield ResultMessage(subtype="success", duration_ms=900, duration_api_ms=800, is_error=False,
                            num_turns=2, session_id="sess-1", total_cost_usd=self.cost,
                            usage={"input_tokens": 10, "cache_read_input_tokens": 3000,
                                   "cache_creation_input_tokens": 1000, "output_tokens": 40},
                            result="No open tasks.")

    async def disconnect(self):
        self.closed = True


def call(server_tool, args):
    return asyncio.run(server_tool.handler(args))


class SdkToolsTest(unittest.TestCase):
    def setUp(self):
        self.planner = Planner(tempfile.mkdtemp(), TODAY, hebcal_opener())

    def tool(self, name):
        return mock.Mock(handler=make_handler(self.planner, name))

    def test_names_are_namespaced(self):
        self.assertIn("mcp__planner__add_task", TOOL_NAMES)
        self.assertEqual(len(TOOL_NAMES), 6)

    def test_handler_runs_shared_tool(self):
        res = call(self.tool("add_task"), {"course": "OS", "title": "Lab", "due": "2026-10-30"})
        self.assertNotIn("is_error", res)
        self.assertEqual(json.loads(res["content"][0]["text"])["added"], "T1|OS|Lab|due 2026-10-30|2h|open")
        self.assertEqual(len(self.planner.store.tasks()), 1)

    def test_handler_returns_error(self):
        res = call(self.tool("complete_task"), {"task_id": "T5"})
        self.assertTrue(res["is_error"])
        res = call(self.tool("add_task"), {"title": "x"})
        self.assertTrue(res["is_error"])

    def test_server_config(self):
        server = build_server(self.planner)
        self.assertEqual(server["type"], "sdk")
        self.assertEqual(server["name"], "planner")


class SdkAgentTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def test_memory_file_from_store(self):
        p = Planner(self.dir, TODAY)
        p.remember("I study at most 3 hours per day")
        write_memory_file(self.dir, p.store)
        content = Path(self.dir, "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("- I study at most 3 hours per day", content)

    def test_options(self):
        o = SdkAgent(self.dir, "s1", TODAY).options
        self.assertEqual(o.model, "claude-opus-5-5")
        self.assertEqual(o.effort, "medium")
        self.assertTrue(o.strict_mcp_config)
        self.assertEqual(o.tools, [])
        self.assertEqual(o.allowed_tools, TOOL_NAMES)
        self.assertEqual(o.setting_sources, ["project"])
        self.assertEqual(o.cwd, self.dir)
        self.assertIn("Study Planner", o.system_prompt)
        self.assertIn("Today is 2026-10-25", o.system_prompt)

    def test_ask_collects_metrics(self):
        async def run():
            agent = SdkAgent(self.dir, "s1", TODAY)
            answer, metrics = await agent.ask("what is open?")
            _, second = await agent.ask("and now?")
            await agent.close()
            self.assertEqual(second["cost_usd"], 0.0123)
            return agent, answer, metrics
        with mock.patch.object(SDK.agent, "ClaudeSDKClient", FakeSdkClient):
            agent, answer, metrics = asyncio.run(run())
        self.assertEqual(answer, "No open tasks.")
        self.assertEqual(metrics["tools"], ["list_tasks"])
        self.assertEqual(metrics["calls"], 2)
        self.assertEqual(metrics["cache_read"], 3000)
        self.assertEqual(metrics["cache_hit_pct"], 74.8)
        self.assertEqual(metrics["cost_usd"], 0.0123)
        self.assertEqual(agent.session_id, "sess-1")
        self.assertTrue(FakeSdkClient.instances[-1].closed)


if __name__ == "__main__":
    unittest.main()
