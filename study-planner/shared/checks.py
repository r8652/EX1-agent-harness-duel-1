def find_tasks(state, course):
    return [t for t in state["tasks"] if course.lower() in t["course"].lower()]


def plan_hours(state):
    totals = {}
    for day, items in state["plan"].get("days", {}).items():
        totals[day] = sum(float(i.split()[1].rstrip("h")) for i in items)
    return totals


def plan_task_ids(state):
    return {i.split()[0] for items in state["plan"].get("days", {}).values() for i in items}


def task_exists(state, turns, course, due):
    found = [t["due"] for t in find_tasks(state, course)]
    return due in found, f"{course}: due dates {found}"


def task_status(state, turns, course, status):
    found = [t["status"] for t in find_tasks(state, course)]
    return found == [status], f"{course}: status {found}"


def task_count(state, turns, n):
    return len(state["tasks"]) == n, f"{len(state['tasks'])} tasks"


def memory_contains(state, turns, words):
    facts = [m["fact"] for m in state["memory"]]
    ok = any(all(w.lower() in f.lower() for w in words) for f in facts)
    return ok, f"memory: {facts}"


def plan_hours_per_day(state, turns, value):
    got = state["plan"].get("hours_per_day")
    return got == value, f"hours_per_day={got}"


def plan_max_hours(state, turns, limit):
    hours = plan_hours(state)
    busiest = max(hours.values(), default=0)
    return bool(hours) and busiest <= limit, f"busiest day {busiest:g}h"


def plan_skips(state, turns, date):
    days = state["plan"].get("days", {})
    return bool(days) and not days.get(date), f"{date}: {days.get(date, 'not in plan')}"


def plan_excludes_task(state, turns, course):
    ids = {t["id"] for t in find_tasks(state, course)}
    used = plan_task_ids(state)
    return bool(state["plan"]) and not ids & used, f"{course} ids {sorted(ids)}, planned {sorted(used)}"


def tool_called(state, turns, tool, session):
    used = [name for t in turns if t["session"] == session for name in t["metrics"]["tools"]]
    return tool in used, f"tools in {session}: {used}"


CHECKS = {f.__name__: f for f in [task_exists, task_status, task_count, memory_contains,
                                  plan_hours_per_day, plan_max_hours, plan_skips,
                                  plan_excludes_task, tool_called]}


def evaluate(checks, snapshots, turns):
    results = []
    for c in checks:
        at = c.get("at", "end")
        state = snapshots[at] if at != "end" else snapshots[list(snapshots)[-1]]
        args = {k: v for k, v in c.items() if k not in ("name", "type", "at")}
        try:
            ok, detail = CHECKS[c["type"]](state, turns, **args)
        except Exception as e:
            ok, detail = False, f"check failed to run: {e}"
        results.append({"name": c["name"], "at": at, "passed": bool(ok), "detail": detail})
    return results
