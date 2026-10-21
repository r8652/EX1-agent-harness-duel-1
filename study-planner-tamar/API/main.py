import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from API.agent import ApiAgent
from shared.runner import run_scenario


def chat(state_dir, session):
    agent = ApiAgent(state_dir, session)
    while True:
        try:
            text = input("\nyou> ").strip()
        except EOFError:
            break
        if text in ("", "exit", "quit"):
            break
        reply, metrics = agent.ask(text)
        print(f"agent> {reply}\n  ({metrics['calls']} calls, ${metrics['cost_usd']})")


def main():
    parser = argparse.ArgumentParser(description="Study planner on the Messages API")
    parser.add_argument("--scenario", help="scenario json file")
    parser.add_argument("--out", default=str(ROOT / "results" / "api.json"))
    parser.add_argument("--state", default=str(ROOT / "state" / "api"))
    parser.add_argument("--session", default="chat", help="history name for chat mode (resumes if it exists)")
    args = parser.parse_args()
    if not args.scenario:
        chat(args.state, args.session)
        return
    asyncio.run(run_scenario("api", args.scenario, args.out, args.state,
                             lambda state, name, today: ApiAgent(state, name, today)))


if __name__ == "__main__":
    main()
