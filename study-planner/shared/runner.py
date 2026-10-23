import inspect
import json
import shutil
from datetime import date
from pathlib import Path

from shared.checks import evaluate
from shared.measure import loc_report
from shared.store import Store


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


def snapshot(state_dir):
    store = Store(state_dir)
    return {"tasks": store.tasks(), "memory": store.memories(), "plan": store.plan()}


async def run_scenario(version, scenario_path, out_path, state_dir, make_agent):
    scenario, today = load_scenario(scenario_path)
    state_dir = Path(state_dir)
    if state_dir.exists():
        shutil.rmtree(state_dir)
    state_dir.mkdir(parents=True)
    turns = []
    snapshots = {}
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
                snapshots[f"{session['name']}:{i}"] = snapshot(state_dir)
        finally:
            if hasattr(agent, "close"):
                await maybe_await(agent.close())
    result = {"version": version, "scenario": str(scenario_path), "today": today.isoformat(),
              "turns": turns, "totals": totals(turns)}
    result["checks"] = evaluate(scenario.get("checks", []), snapshots, turns)
    result["passed"] = f"{sum(c['passed'] for c in result['checks'])}/{len(result['checks'])}"
    result["loc"] = loc_report()
    for c in result["checks"]:
        print(f"[{'PASS' if c['passed'] else 'FAIL'}] {c['name']} ({c['at']}): {c['detail']}", flush=True)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nresults written to {out_path}", flush=True)
    return result
