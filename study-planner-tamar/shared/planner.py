import re
from datetime import date, timedelta

from shared.calendar_api import blocked_days, CalendarError
from shared.store import Store

LIST_LIMIT = 8
DEFAULT_HOURS_PER_DAY = 4


class ToolError(Exception):
    pass


def parse_date(value, field):
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ToolError(f"{field} must be YYYY-MM-DD, got {value!r}")


def task_line(t):
    return f"{t['id']}|{t['course']}|{t['title']}|due {t['due']}|{t['hours']:g}h|{t['status']}"


# Study planner domain logic shared by the API and SDK versions
class Planner:
    def __init__(self, state_dir, today=None, opener=None):
        self.store = Store(state_dir)
        self.today = today or date.today()
        self.opener = opener

    def add_task(self, course, title, due, hours=2):
        due_d = parse_date(due, "due")
        if due_d < self.today:
            raise ToolError(f"due date {due} is in the past (today {self.today})")
        try:
            hours = float(hours)
        except (TypeError, ValueError):
            raise ToolError("hours must be a number")
        if hours <= 0 or hours > 100:
            raise ToolError("hours must be between 0 and 100")
        course, title = str(course).strip(), str(title).strip()
        if not course or not title:
            raise ToolError("course and title are required")
        tasks = self.store.tasks()
        for t in tasks:
            if t["course"].lower() == course.lower() and t["title"].lower() == title.lower():
                raise ToolError(f"task already exists as {t['id']}")
        next_id = max([int(t["id"][1:]) for t in tasks] + [0]) + 1
        task = {"id": f"T{next_id}", "course": course, "title": title,
                "due": due_d.isoformat(), "hours": hours, "status": "open"}
        tasks.append(task)
        self.store.save_tasks(tasks)
        return {"added": task_line(task)}

    def list_tasks(self, course=None, days=None, status="open"):
        if status not in ("open", "done", "all"):
            raise ToolError("status must be open, done or all")
        tasks = self.store.tasks()
        if status != "all":
            tasks = [t for t in tasks if t["status"] == status]
        if course:
            tasks = [t for t in tasks if course.lower() in t["course"].lower()]
        if days is not None:
            limit = self.today + timedelta(days=int(days))
            tasks = [t for t in tasks if date.fromisoformat(t["due"]) <= limit]
        tasks.sort(key=lambda t: t["due"])
        result = {"count": len(tasks), "tasks": [task_line(t) for t in tasks[:LIST_LIMIT]]}
        if len(tasks) > LIST_LIMIT:
            result["more"] = len(tasks) - LIST_LIMIT
        return result

    def complete_task(self, task_id):
        tasks = self.store.tasks()
        for t in tasks:
            if t["id"].lower() == str(task_id).strip().lower():
                if t["status"] == "done":
                    raise ToolError(f"{t['id']} is already done")
                t["status"] = "done"
                t["done_on"] = self.today.isoformat()
                self.store.save_tasks(tasks)
                return {"done": task_line(t)}
        raise ToolError(f"no task with id {task_id}")

    def jewish_calendar(self, start, end):
        start_d, end_d = parse_date(start, "start"), parse_date(end, "end")
        if end_d < start_d:
            raise ToolError("end is before start")
        if (end_d - start_d).days > 62:
            raise ToolError("range is limited to 62 days")
        try:
            blocked, events = blocked_days(start_d, end_d, self.opener)
        except CalendarError as e:
            raise ToolError(str(e))
        return {"blocked": blocked, "events": events[:LIST_LIMIT]}

    def plan_week(self, start=None, hours_per_day=DEFAULT_HOURS_PER_DAY, blocked=None):
        start_d = parse_date(start, "start") if start else self.today
        try:
            hours_per_day = float(hours_per_day)
        except (TypeError, ValueError):
            raise ToolError("hours_per_day must be a number")
        if hours_per_day <= 0 or hours_per_day > 16:
            raise ToolError("hours_per_day must be between 0 and 16")
        blocked = set(blocked or [])
        for b in blocked:
            parse_date(b, "blocked")
        days = []
        for i in range(7):
            d = start_d + timedelta(days=i)
            if d.weekday() != 5 and d.isoformat() not in blocked:
                days.append(d)
        free = {d: hours_per_day for d in days}
        plan = {d.isoformat(): [] for d in days}
        unscheduled = []
        open_tasks = sorted([t for t in self.store.tasks() if t["status"] == "open"],
                            key=lambda t: t["due"])
        for t in open_tasks:
            left = t["hours"]
            due_d = date.fromisoformat(t["due"])
            for d in days:
                if left <= 0 or d > due_d:
                    break
                take = min(left, free[d])
                if take > 0:
                    plan[d.isoformat()].append(f"{t['id']} {take:g}h")
                    free[d] -= take
                    left -= take
            if left > 0 and due_d <= start_d + timedelta(days=6):
                unscheduled.append(f"{t['id']} {left:g}h")
        saved = {"start": start_d.isoformat(), "hours_per_day": hours_per_day,
                 "blocked": sorted(blocked), "days": plan, "unscheduled": unscheduled}
        self.store.save_plan(saved)
        result = {"days": {k: v for k, v in plan.items() if v}, "skipped": sorted(
            (start_d + timedelta(days=i)).isoformat() for i in range(7)
            if (start_d + timedelta(days=i)) not in free)}
        if unscheduled:
            result["unscheduled"] = unscheduled
        return result

    def remember(self, fact, tags=None):
        fact = str(fact).strip()
        if not fact:
            raise ToolError("fact is empty")
        if len(fact) > 300:
            raise ToolError("fact is too long (max 300 chars)")
        items = self.store.memories()
        for m in items:
            if m["fact"].lower() == fact.lower():
                return {"exists": m["id"]}
        tags = [str(t).lower() for t in (tags or [])]
        next_id = max([int(m["id"][1:]) for m in items] + [0]) + 1
        item = {"id": f"M{next_id}", "fact": fact, "tags": tags, "saved": self.today.isoformat()}
        items.append(item)
        self.store.save_memories(items)
        return {"saved": item["id"]}

    def summary_line(self):
        open_tasks = [t for t in self.store.tasks() if t["status"] == "open"]
        if not open_tasks:
            return "no open tasks"
        nearest = min(open_tasks, key=lambda t: t["due"])
        return f"{len(open_tasks)} open tasks, nearest: {nearest['id']} due {nearest['due']}"


WORD = re.compile(r"[a-z0-9֐-׿]+")
STOP = {"the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "is", "it", "my", "me",
        "i", "you", "what", "do", "can", "please", "with", "at", "this", "that", "be", "are"}


def words(text):
    return {w for w in WORD.findall(text.lower()) if w not in STOP and len(w) > 1}


# Picks the memories that share words or tags with the message, best match first
def relevant_memories(items, message, limit=3):
    msg = words(message)
    scored = []
    for m in items:
        score = len(msg & (words(m["fact"]) | set(m.get("tags", []))))
        if score:
            scored.append((score, m["id"], m))
    scored.sort(key=lambda s: (-s[0], s[1]))
    return [m for _, _, m in scored[:limit]]
