DATE = {"type": "string", "description": "YYYY-MM-DD"}

TOOL_SPECS = [
    {
        "name": "add_task",
        "description": "Add an assignment/exam to study.",
        "input_schema": {
            "type": "object",
            "properties": {
                "course": {"type": "string"},
                "title": {"type": "string"},
                "due": DATE,
                "hours": {"type": "number", "description": "estimated work hours"},
            },
            "required": ["course", "title", "due"],
        },
    },
    {
        "name": "list_tasks",
        "description": "List tasks sorted by due date. Lines: id|course|title|due|hours|status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "course": {"type": "string"},
                "days": {"type": "integer", "description": "only tasks due within N days"},
                "status": {"type": "string", "enum": ["open", "done", "all"]},
            },
        },
    },
    {
        "name": "complete_task",
        "description": "Mark a task as done.",
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "string", "description": "e.g. T3"}},
            "required": ["task_id"],
        },
    },
    {
        "name": "get_jewish_calendar",
        "description": "Shabbat and Israeli holidays from Hebcal. Returns blocked (no-study) days.",
        "input_schema": {
            "type": "object",
            "properties": {"start": DATE, "end": DATE},
            "required": ["start", "end"],
        },
    },
    {
        "name": "plan_week",
        "description": "Build and save a 7-day study plan from open tasks, earliest due first. Skips Saturday and blocked days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start": DATE,
                "hours_per_day": {"type": "number"},
                "blocked": {"type": "array", "items": DATE, "description": "holiday dates to skip"},
            },
        },
    },
    {
        "name": "remember",
        "description": "Save a lasting user preference or decision for future sessions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fact": {"type": "string", "description": "one short sentence"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["fact"],
        },
    },
]

TOOL_METHODS = {
    "add_task": "add_task",
    "list_tasks": "list_tasks",
    "complete_task": "complete_task",
    "get_jewish_calendar": "jewish_calendar",
    "plan_week": "plan_week",
    "remember": "remember",
}

SYSTEM_PROMPT = """You are Study Planner, a study assistant for a university student.
You manage their assignments with the tools: add, list, complete, plan the week.
Rules:
- Never plan study on Shabbat or Jewish holidays. Before plan_week, call get_jewish_calendar for the same 7 days and pass the holiday dates as blocked.
- When the user states a lasting preference or decision, save it with remember.
- Use saved preferences (e.g. hours per day) when you plan.
- Get tasks with list_tasks instead of guessing. Use filters to fetch only what you need.
- Answer briefly, in the language the user writes in."""


# Calls the planner method behind a tool name with the model's input
def run_tool(planner, name, args):
    method = TOOL_METHODS.get(name)
    if method is None:
        raise KeyError(name)
    return getattr(planner, method)(**args)
