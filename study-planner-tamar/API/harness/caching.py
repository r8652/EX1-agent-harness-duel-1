from API.harness import log

EPHEMERAL = {"type": "ephemeral"}


def cached_system(text):
    log(__file__, "breakpoint 1: tools + system prompt")
    return [{"type": "text", "text": text, "cache_control": EPHEMERAL}]


def conversation_cache():
    return {"cache_control": EPHEMERAL}
