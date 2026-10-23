import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import API.harness
from anthropic.types import Message

API.harness.VERBOSE = False


def usage(inp=1000, out=50, read=0, write=0):
    return {"input_tokens": inp, "output_tokens": out,
            "cache_read_input_tokens": read, "cache_creation_input_tokens": write}


def reply(content, stop="end_turn", **u):
    return Message.model_validate({
        "id": "msg_test", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
        "content": content, "stop_reason": stop, "stop_sequence": None, "usage": usage(**u)})


def text(t, **u):
    return reply([{"type": "text", "text": t}], **u)


def tool_call(*calls, **u):
    blocks = [{"type": "thinking", "thinking": "", "signature": "sig"}]
    for i, (name, args) in enumerate(calls):
        blocks.append({"type": "tool_use", "id": f"toolu_{name}_{i}", "name": name, "input": args})
    return reply(blocks, stop="tool_use", **u)


class FakeClient:
    def __init__(self, script):
        self.script = list(script)
        self.requests = []
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **kwargs):
        self.requests.append(json.loads(json.dumps(kwargs, default=str)))
        if not self.script:
            raise AssertionError("fake client ran out of responses")
        return self.script.pop(0)


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def hebcal_opener(items=None, fail=False):
    seen = []

    def opener(url, timeout=None):
        seen.append(url)
        if fail:
            raise OSError("network down")
        return FakeResponse(json.dumps({"items": items or []}).encode("utf-8"))
    opener.seen = seen
    return opener
