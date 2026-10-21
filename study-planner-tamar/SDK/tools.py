import json

from claude_agent_sdk import create_sdk_mcp_server, tool

from shared.planner import ToolError
from shared.tool_specs import TOOL_SPECS, run_tool

SERVER = "planner"
TOOL_NAMES = [f"mcp__{SERVER}__{spec['name']}" for spec in TOOL_SPECS]


def make_handler(planner, name):
    async def handler(args):
        try:
            data = run_tool(planner, name, args)
            text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
            return {"content": [{"type": "text", "text": text}]}
        except (ToolError, TypeError) as e:
            return {"content": [{"type": "text", "text": str(e)}], "is_error": True}
    return handler


def build_server(planner):  # replaces tools.py
    tools = [tool(s["name"], s["description"], s["input_schema"])(make_handler(planner, s["name"]))
             for s in TOOL_SPECS]
    return create_sdk_mcp_server(name=SERVER, version="1.0.0", tools=tools)
