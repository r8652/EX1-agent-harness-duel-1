import json
from pathlib import Path


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, name):
        return self.root / name

    def read(self, name, default):
        p = self.path(name)
        if not p.exists():
            return default
        return json.loads(p.read_text(encoding="utf-8"))

    def write(self, name, data):
        p = self.path(name)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(p)

    def tasks(self):
        return self.read("tasks.json", [])

    def save_tasks(self, tasks):
        self.write("tasks.json", tasks)

    def memories(self):
        return self.read("memory.json", [])

    def save_memories(self, items):
        self.write("memory.json", items)

    def plan(self):
        return self.read("plan.json", {})

    def save_plan(self, plan):
        self.write("plan.json", plan)
