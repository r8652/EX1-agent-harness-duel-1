import json

from API.harness import log

SUMMARY_PROMPT = """Summarize this conversation between a student and her study planner assistant.
Keep: tasks that were added, completed or discussed (with ids and dates), the latest plan,
preferences and decisions, and any open question. Drop greetings and repeated tool output.
Write plain text, at most 150 words."""


def render(messages):
    out = []
    for m in messages:
        for b in m["content"]:
            kind = b.get("type")
            if kind == "text":
                out.append(f"{m['role']}: {b['text']}")
            elif kind == "tool_use":
                out.append(f"tool call {b['name']} {json.dumps(b['input'], ensure_ascii=False)}")
            elif kind == "tool_result":
                out.append(f"tool result: {str(b['content'])[:300]}")
    return "\n".join(out)


class Compactor:
    def __init__(self, client, model, threshold):
        self.client = client
        self.model = model
        self.threshold = threshold

    def needed(self, last_prompt_tokens):
        return self.threshold and last_prompt_tokens > self.threshold

    def summarize(self, messages, meter):
        log(__file__, f"history over {self.threshold} tokens, summarizing {len(messages)} messages")
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=SUMMARY_PROMPT,
            messages=[{"role": "user", "content": render(messages)}],
            output_config={"effort": "low"},
        )
        meter.add(resp.usage, label="compaction")
        summary = "".join(b.text for b in resp.content if b.type == "text").strip()
        log(__file__, f"summary: {len(summary)} chars")
        return summary
