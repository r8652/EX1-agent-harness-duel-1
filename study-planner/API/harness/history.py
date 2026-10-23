import json
from pathlib import Path

from API.harness import log


class History:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.messages = []
        self.summary = None
        if self.path.exists():
            self._load()

    def _load(self):
        for line in self.path.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if rec.get("type") == "compaction":
                self.messages = []
                self.summary = rec["summary"]
            else:
                self.messages.append(rec)
        log(__file__, f"resumed {len(self.messages)} messages from {self.path.name}")

    def _write(self, rec):
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def append(self, message):
        self.messages.append(message)
        self._write(message)
        log(__file__, f"appended {message['role']} message (#{len(self.messages)})")

    def compact(self, summary):
        self._write({"type": "compaction", "summary": summary})
        self.messages = []
        self.summary = summary
        log(__file__, "compaction record written, new segment started")

    def take_summary(self):
        summary, self.summary = self.summary, None
        return summary if not self.messages else None
