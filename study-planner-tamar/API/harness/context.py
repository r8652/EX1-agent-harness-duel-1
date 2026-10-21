from API.harness import log


def build_user_turn(message, planner, memories, summary=None):
    lines = [f"today: {planner.today.isoformat()} ({planner.today.strftime('%A')})",
             f"state: {planner.summary_line()}"]
    if memories:
        lines.append("saved preferences:")
        lines.extend(f"- {m['fact']}" for m in memories)
    if summary:
        lines.append(f"earlier conversation summary: {summary}")
    context = "<context>\n" + "\n".join(lines) + "\n</context>"
    log(__file__, f"context block: {len(lines)} lines, {len(memories)} memories, "
                  f"summary={'yes' if summary else 'no'}")
    return {"role": "user", "content": [{"type": "text", "text": context},
                                        {"type": "text", "text": message}]}
