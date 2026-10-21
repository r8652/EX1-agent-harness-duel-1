import inspect
import json
import shutil
from datetime import date
from pathlib import Path


async def maybe_await(value):
    if inspect.isawaitable(value):
        return await value
    return value


def load_scenario(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    today = date.fromisoformat(data["today"]) if data.get("today") else date.today()
    return data, today


def totals(turns):
    keys = ["input", "cache_read", "cache_write", "output", "calls", "cost_usd", "seconds"]
    tot = {k: round(sum(t["metrics"][k] for t in turns), 6) for k in keys}
    prompt = tot["input"] + tot["cache_read"] + tot["cache_write"]
    tot["cache_hit_pct"] = round(100 * tot["cache_read"] / prompt, 1) if prompt else 0.0
    return tot


async def run_scenario(version, scenario_path, out_path, state_dir, make_agent, extra=None):
    scenario, today = load_scenario(scenario_path)
    state_dir = Path(state_dir)
    if state_dir.exists():
        shutil.rmtree(state_dir)
    state_dir.mkdir(parents=True)
    turns = []
    for session in scenario["sessions"]:
        print(f"\n===== {version}: session {session['name']} =====", flush=True)
        agent = make_agent(state_dir, session["name"], today)
        try:
            for i, message in enumerate(session["messages"], 1):
                print(f"\n--- user: {message}", flush=True)
                reply, metrics = await maybe_await(agent.ask(message))
                print(f"--- agent: {reply}", flush=True)
                turns.append({"session": session["name"], "turn": i, "user": message,
                              "reply": reply, "metrics": metrics})
        finally:
            if hasattr(agent, "close"):
                await maybe_await(agent.close())
    result = {"version": version, "scenario": str(scenario_path), "today": today.isoformat(),
              "turns": turns, "totals": totals(turns)}
    if extra:
        result.update(extra(state_dir, turns))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nresults written to {out_path}", flush=True)
    return result
