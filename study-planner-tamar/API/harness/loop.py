from API.harness import log

MAX_CALLS = 15


def final_text(content):
    return "".join(b.text for b in content if b.type == "text").strip()


def run_turn(client, request, history, dispatcher, meter):
    while meter.calls < MAX_CALLS:
        log(__file__, f"calling model with {len(history.messages)} messages")
        resp = client.messages.create(**request, messages=history.messages)
        meter.add(resp.usage)
        history.append({"role": "assistant",
                        "content": [b.to_dict(mode="json") for b in resp.content]})
        log(__file__, f"stop_reason={resp.stop_reason}")
        if resp.stop_reason == "tool_use":
            results = dispatcher.run_all(resp.content, meter)
            history.append({"role": "user", "content": results})
            continue
        if resp.stop_reason == "refusal":
            return "The request was declined."
        if resp.stop_reason == "max_tokens":
            log(__file__, "response cut by max_tokens")
        return final_text(resp.content)
    log(__file__, f"stopped after {MAX_CALLS} model calls")
    return "Stopped: too many steps for one request."
