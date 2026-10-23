import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARTS = ["loop", "tools", "history", "memory", "context", "compaction", "caching", "tokens"]
MARK = re.compile(r"#\s*replaces\s+(.+)$")


def code_lines(lines):
    return sum(1 for l in lines if l.strip() and not l.strip().startswith("#"))


def file_loc(path):
    return code_lines(Path(path).read_text(encoding="utf-8").splitlines())


def marked_span(tree, lines, lineno):
    if lines[lineno - 1].strip().startswith(("def ", "async def ")):
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.lineno == lineno:
                return code_lines(lines[node.lineno - 1:node.end_lineno])
    starts = [n.lineno for n in ast.walk(tree)
              if isinstance(n, (ast.stmt, ast.keyword)) and getattr(n, "end_lineno", None) == lineno]
    return code_lines(lines[min(starts) - 1:lineno]) if starts else 1


def sdk_parts():
    parts = {p: 0 for p in PARTS}
    for path in (ROOT / "SDK").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        tree = ast.parse(text)
        for i, line in enumerate(lines, 1):
            m = MARK.search(line)
            if not m:
                continue
            for name in m.group(1).split(","):
                part = name.strip().removesuffix(".py")
                if part in parts:
                    parts[part] += marked_span(tree, lines, i)
    return parts


def loc_report():
    api = {p: file_loc(ROOT / "API" / "harness" / f"{p}.py") for p in PARTS}
    return {
        "api_harness": api,
        "sdk_replacement": sdk_parts(),
        "files": {
            "API/harness (all)": sum(file_loc(p) for p in (ROOT / "API" / "harness").glob("*.py")),
            "API/agent.py": file_loc(ROOT / "API" / "agent.py"),
            "API/main.py": file_loc(ROOT / "API" / "main.py"),
            "SDK/agent.py": file_loc(ROOT / "SDK" / "agent.py"),
            "SDK/tools.py": file_loc(ROOT / "SDK" / "tools.py"),
            "SDK/main.py": file_loc(ROOT / "SDK" / "main.py"),
            "shared (both)": sum(file_loc(p) for p in (ROOT / "shared").glob("*.py")),
        },
    }
