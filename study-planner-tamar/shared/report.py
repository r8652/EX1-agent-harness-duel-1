import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shared.measure import PARTS, loc_report

ROWS = [
    ("input tokens", "input", "{:,}"),
    ("cache read tokens", "cache_read", "{:,}"),
    ("cache write tokens", "cache_write", "{:,}"),
    ("output tokens", "output", "{:,}"),
    ("cache hit (% of prompt)", "cache_hit_pct", "{}%"),
    ("model calls", "calls", "{}"),
    ("cost (USD)", "cost_usd", "${:.4f}"),
    ("time (s)", "seconds", "{:.1f}"),
]


def load(name):
    p = ROOT / "results" / f"{name}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def cell(res, key, fmt):
    return fmt.format(res["totals"][key]) if res else "—"


def results_table(api, sdk):
    lines = ["| | API | SDK |", "|---|---|---|"]
    lines += [f"| {label} | {cell(api, k, f)} | {cell(sdk, k, f)} |" for label, k, f in ROWS]
    lines.append(f"| checks passed | {api['passed'] if api else '—'} | {sdk['passed'] if sdk else '—'} |")
    return "\n".join(lines)


def turns_table(res):
    if not res:
        return "—"
    lines = ["| turn | input | cache read | cache write | output | calls | tools | cost |",
             "|---|---|---|---|---|---|---|---|"]
    for t in res["turns"]:
        m = t["metrics"]
        lines.append(f"| {t['session']}:{t['turn']} | {m['input']} | {m['cache_read']} | {m['cache_write']} "
                     f"| {m['output']} | {m['calls']} | {', '.join(m['tools']) or '-'} | ${m['cost_usd']:.4f} |")
    return "\n".join(lines)


def checks_table(api, sdk):
    base = sdk or api
    if not base:
        return "—"
    lines = ["| check | API | SDK |", "|---|---|---|"]
    for i, c in enumerate(base["checks"]):
        a = ("PASS" if api["checks"][i]["passed"] else "FAIL") if api else "—"
        s = ("PASS" if sdk["checks"][i]["passed"] else "FAIL") if sdk else "—"
        lines.append(f"| {c['name']} | {a} | {s} |")
    return "\n".join(lines)


def loc_table():
    rep = loc_report()
    lines = ["| part | API (harness file) | SDK (lines marked `# replaces`) |", "|---|---|---|"]
    for p in PARTS:
        lines.append(f"| {p} | {rep['api_harness'][p]} | {rep['sdk_replacement'][p]} |")
    lines.append(f"| **total** | **{sum(rep['api_harness'].values())}** | **{sum(rep['sdk_replacement'].values())}** |")
    files = ", ".join(f"{k}: {v}" for k, v in rep["files"].items())
    return "\n".join(lines) + f"\n\nAll code lines (no blanks): {files}."


def fill(text, name, body):
    pattern = re.compile(rf"(<!-- {name} -->).*?(<!-- /{name} -->)", re.S)
    return pattern.sub(lambda m: m.group(1) + "\n" + body + "\n" + m.group(2), text)


def main():
    api, sdk = load("api"), load("sdk")
    path = ROOT / "REPORT.md"
    text = path.read_text(encoding="utf-8")
    text = fill(text, "results", results_table(api, sdk))
    text = fill(text, "checks", checks_table(api, sdk))
    text = fill(text, "loc", loc_table())
    text = fill(text, "turns-api", turns_table(api))
    text = fill(text, "turns-sdk", turns_table(sdk))
    path.write_text(text, encoding="utf-8")
    print(f"updated {path}")


if __name__ == "__main__":
    main()
