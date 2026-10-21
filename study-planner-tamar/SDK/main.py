import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from SDK.agent import SdkAgent
from shared.runner import run_scenario


async def chat(state_dir, resume):
    Path(state_dir).mkdir(parents=True, exist_ok=True)
    agent = SdkAgent(state_dir, "chat", resume=resume)
    try:
        while True:
            try:
                text = input("\nyou> ").strip()
            except EOFError:
                break
            if text in ("", "exit", "quit"):
                break
            reply, metrics = await agent.ask(text)
            print(f"agent> {reply}\n  ({metrics['calls']} calls, ${metrics['cost_usd']})")
    finally:
        await agent.close()
        if agent.session_id:
            print(f"session id: {agent.session_id} (continue with --resume)")


def main():
    parser = argparse.ArgumentParser(description="Study planner on the Claude Agent SDK")
    parser.add_argument("--scenario", help="scenario json file")
    parser.add_argument("--out", default=str(ROOT / "results" / "sdk.json"))
    parser.add_argument("--state", default=str(ROOT / "state" / "sdk"))
    parser.add_argument("--resume", help="session id to continue in chat mode")
    args = parser.parse_args()
    if not args.scenario:
        asyncio.run(chat(args.state, args.resume))
        return
    asyncio.run(run_scenario("sdk", args.scenario, args.out, args.state,
                             lambda state, name, today: SdkAgent(state, name, today)))


if __name__ == "__main__":
    main()
