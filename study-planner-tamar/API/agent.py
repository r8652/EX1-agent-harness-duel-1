from pathlib import Path

from API.harness import log
from API.harness.caching import cached_system, conversation_cache
from API.harness.compaction import Compactor
from API.harness.context import build_user_turn
from API.harness.history import History
from API.harness.loop import run_turn
from API.harness.memory import Memory
from API.harness.tokens import TurnMeter
from API.harness.tools import Dispatcher, tool_definitions
from shared.planner import Planner
from shared.tool_specs import SYSTEM_PROMPT

MODEL = "claude-opus-5-5"
EFFORT = "medium"
COMPACT_AT = 9000


# Study planner agent running on the Messages API with the hand-written harness
class ApiAgent:
    def __init__(self, state_dir, session, today=None, client=None, compact_at=COMPACT_AT):
        if client is None:
            import anthropic
            client = anthropic.Anthropic()
        self.client = client
        self.planner = Planner(state_dir, today)
        self.memory = Memory(self.planner.store)
        self.history = History(Path(state_dir) / "history" / f"{session}.jsonl")
        self.dispatcher = Dispatcher(self.planner)
        self.compactor = Compactor(client, MODEL, compact_at)
        self.last_prompt_tokens = 0
        self.request = {
            "model": MODEL,
            "max_tokens": 16000,
            "system": cached_system(SYSTEM_PROMPT),
            "tools": tool_definitions(),
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": EFFORT},
            **conversation_cache(),
        }
        log(__file__, f"agent ready: session={session}, model={MODEL}, effort={EFFORT}")

    def ask(self, message):
        meter = TurnMeter(MODEL)
        if self.history.messages and self.compactor.needed(self.last_prompt_tokens):
            self.history.compact(self.compactor.summarize(self.history.messages, meter))
        turn = build_user_turn(message, self.planner, self.memory.recall(message),
                               self.history.take_summary())
        self.history.append(turn)
        reply = run_turn(self.client, self.request, self.history, self.dispatcher, meter)
        self.last_prompt_tokens = meter.last_prompt_tokens
        return reply, meter.result()
