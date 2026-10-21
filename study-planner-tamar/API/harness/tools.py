import copy
import json

from API.harness import log
from shared.planner import ToolError
from shared.tool_specs import TOOL_SPECS, run_tool

MAX_RESULT_CHARS = 1500


# JSON schemas sent to the model, in a fixed order so the cached prefix never changes
def tool_definitions():
    return copy.deepcopy(TOOL_SPECS)


def compact(data):
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if len(text) > MAX_RESULT_CHARS:
        text = text[:MAX_RESULT_CHARS] + "...(truncated)"
    return text


# Runs the tool_use blocks of one model response and builds the tool_result blocks
class Dispatcher:
    def __init__(self, planner):
        self.planner = planner

    def run(self, block, meter):
        meter.tool(block.name)
        args = block.input if isinstance(block.input, dict) else {}
        try:
            content = compact(run_tool(self.planner, block.name, args))
            is_error = False
        except KeyError:
            content, is_error = f"unknown tool {block.name}", True
        except ToolError as e:
            content, is_error = str(e), True
        except TypeError as e:
            content, is_error = f"bad arguments: {e}", True
        log(__file__, f"{block.name}({compact(args)}) -> {'ERROR ' if is_error else ''}{content[:120]}")
        result = {"type": "tool_result", "tool_use_id": block.id, "content": content}
        if is_error:
            result["is_error"] = True
        return result

    def run_all(self, blocks, meter):
        return [self.run(b, meter) for b in blocks if b.type == "tool_use"]
