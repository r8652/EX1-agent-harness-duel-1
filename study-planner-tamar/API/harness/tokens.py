import time

from API.harness import log

PRICES = {
    "claude-opus-5-5": {"input": 4.00, "cache_write": 5.00, "cache_read": 0.20, "output": 20.00},
}


def cost_usd(model, usage):
    p = PRICES[model]
    return (usage["input"] * p["input"] + usage["cache_write"] * p["cache_write"]
            + usage["cache_read"] * p["cache_read"] + usage["output"] * p["output"]) / 1_000_000


# Collects token usage, model calls, tools and time for one user turn
class TurnMeter:
    def __init__(self, model):
        self.model = model
        self.usage = {"input": 0, "cache_read": 0, "cache_write": 0, "output": 0}
        self.calls = 0
        self.tools = []
        self.last_prompt_tokens = 0
        self.started = time.perf_counter()

    def add(self, usage, label="loop"):
        read = usage.cache_read_input_tokens or 0
        write = usage.cache_creation_input_tokens or 0
        self.usage["input"] += usage.input_tokens
        self.usage["cache_read"] += read
        self.usage["cache_write"] += write
        self.usage["output"] += usage.output_tokens
        self.calls += 1
        if label == "loop":
            self.last_prompt_tokens = usage.input_tokens + read + write
        log(__file__, f"{label} call {self.calls}: in={usage.input_tokens} cache_read={read} "
                      f"cache_write={write} out={usage.output_tokens}")

    def tool(self, name):
        self.tools.append(name)

    def result(self):
        usage = dict(self.usage)
        prompt = usage["input"] + usage["cache_read"] + usage["cache_write"]
        res = {
            **usage,
            "calls": self.calls,
            "tools": self.tools,
            "cache_hit_pct": round(100 * usage["cache_read"] / prompt, 1) if prompt else 0.0,
            "cost_usd": round(cost_usd(self.model, usage), 6),
            "seconds": round(time.perf_counter() - self.started, 2),
        }
        log(__file__, f"turn total: {res['calls']} calls, ${res['cost_usd']}, cache hit {res['cache_hit_pct']}%")
        return res
