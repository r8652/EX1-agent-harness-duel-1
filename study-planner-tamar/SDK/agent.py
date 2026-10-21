import time
from pathlib import Path

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient,
                              ResultMessage, TextBlock, ToolUseBlock)

from SDK.tools import TOOL_NAMES, build_server
from shared.planner import Planner
from shared.tool_specs import SYSTEM_PROMPT

MODEL = "claude-opus-5-5"
EFFORT = "medium"


def write_memory_file(state_dir, store):
    lines = ["# Study Planner memory", "Saved preferences and decisions of the user:"]
    lines += [f"- {m['fact']}" for m in store.memories()] or ["- (none yet)"]
    Path(state_dir, "CLAUDE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


class SdkAgent:
    def __init__(self, state_dir, session, today=None, resume=None):
        self.planner = Planner(state_dir, today)
        write_memory_file(state_dir, self.planner.store)  # replaces memory.py
        self.options = ClaudeAgentOptions(
            model=MODEL,
            effort=EFFORT,
            system_prompt=f"{SYSTEM_PROMPT}\nToday is {self.planner.today.isoformat()} "
                          f"({self.planner.today.strftime('%A')}).",  # replaces context.py
            mcp_servers={"planner": build_server(self.planner)},
            strict_mcp_config=True,
            tools=[],
            allowed_tools=TOOL_NAMES,
            setting_sources=["project"],
            cwd=str(state_dir),
            resume=resume,  # replaces history.py
        )
        self.client = None
        self.session_id = None
        self.session_cost = 0.0

    async def ask(self, message):
        if self.client is None:
            self.client = ClaudeSDKClient(self.options)  # replaces compaction.py, caching.py
            await self.client.connect()
        started = time.perf_counter()
        tools, texts, result = [], [], None
        await self.client.query(message)  # replaces loop.py
        async for msg in self.client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, ToolUseBlock):
                        tools.append(block.name.split("__")[-1])
                        print(f"[sdk] tool {block.name.split('__')[-1]}({block.input})", flush=True)
                    elif isinstance(block, TextBlock):
                        texts.append(block.text)
            elif isinstance(msg, ResultMessage):
                result = msg
        self.session_id = result.session_id
        return (result.result or "\n".join(texts)).strip(), self.metrics(result, tools, started)

    def metrics(self, result, tools, started):  # replaces tokens.py
        usage = result.usage or {}
        read = usage.get("cache_read_input_tokens", 0)
        write = usage.get("cache_creation_input_tokens", 0)
        prompt = usage.get("input_tokens", 0) + read + write
        return {
            "input": usage.get("input_tokens", 0),
            "cache_read": read,
            "cache_write": write,
            "output": usage.get("output_tokens", 0),
            "calls": result.num_turns,
            "tools": tools,
            "cache_hit_pct": round(100 * read / prompt, 1) if prompt else 0.0,
            "cost_usd": round(self.turn_cost(result), 6),
            "seconds": round(time.perf_counter() - started, 2),
            "model_usage": result.model_usage or {},
        }

    def turn_cost(self, result):  # replaces tokens.py
        total = result.total_cost_usd or 0.0
        cost, self.session_cost = total - self.session_cost, total
        return cost

    async def close(self):
        if self.client is not None:
            await self.client.disconnect()
