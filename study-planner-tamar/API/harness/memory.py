from API.harness import log
from shared.planner import relevant_memories


class Memory:
    def __init__(self, store, limit=3):
        self.store = store
        self.limit = limit
        log(__file__, f"loaded {len(store.memories())} memories from {store.path('memory.json')}")

    def recall(self, message):
        items = self.store.memories()
        picked = relevant_memories(items, message, self.limit)
        log(__file__, f"recall: {len(picked)}/{len(items)} memories match the message "
                      f"{[m['id'] for m in picked]}")
        return picked
