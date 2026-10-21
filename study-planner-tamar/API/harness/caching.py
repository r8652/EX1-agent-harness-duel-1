from API.harness import log

EPHEMERAL = {"type": "ephemeral"}


# Marks the frozen system prompt as a cache breakpoint (tools render before it, so they are cached too)
def cached_system(text):
    log(__file__, "breakpoint 1: tools + system prompt")
    return [{"type": "text", "text": text, "cache_control": EPHEMERAL}]


# Top-level cache_control moves a breakpoint to the last block, so the growing history is reused
def conversation_cache():
    return {"cache_control": EPHEMERAL}
