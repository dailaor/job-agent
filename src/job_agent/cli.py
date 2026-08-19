from __future__ import annotations

import argparse
import asyncio
import json
import shutil
from pathlib import Path
from typing import Any, Sequence

from .connectors.boss import BossConnector
from .service import AgentService


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="job-agent")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--database", default=".job-agent/job-agent.sqlite3")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Create config.json from the example without overwriting")
    serve = sub.add_parser("serve", help="Start the local dashboard")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    sub.add_parser("seed-demo")
    discover = sub.add_parser("discover")
    discover.add_argument("--channel", default="all", help="all, official, or a registered channel ID")
    sub.add_parser("evaluate")
    plan = sub.add_parser("plan")
    plan.add_argument("--channel", required=True, help="boss, official, or a registered channel ID")
    execute = sub.add_parser("execute")
    execute.add_argument("--channel", required=True, help="boss, official, or a registered channel ID")
    execute.add_argument("--live", action="store_true", help="Actually change website state")
    replies = sub.add_parser("check-replies")
    replies.add_argument("--send-resume", action="store_true")
    receipt = sub.add_parser("check-receipts")
    receipt.set_defaults(command="check-receipts")
    login = sub.add_parser("boss-login")
    login.add_argument("--timeout", type=int, default=5)
    cycle = sub.add_parser("run-cycle")
    cycle.add_argument("--live", action="store_true")
    return parser


async def _run(args: argparse.Namespace) -> int:
    if args.command == "init":
        target = Path(args.config)
        if target.exists():
            _print({"status": "unchanged", "message": f"{target} already exists"})
            return 0
        example = Path(__file__).resolve().parents[2] / "config.example.json"
        if not example.exists():
            example = Path("config.example.json")
        shutil.copyfile(example, target)
        _print({"status": "created", "path": str(target)})
        return 0
    service = AgentService(args.config, args.database)
    if args.command == "serve":
        from .web import serve
        serve(service, args.host, args.port)
        return 0
    agent = service.agent()
    if args.command == "seed-demo":
        _print(agent.seed_demo())
    elif args.command == "discover":
        _print(await agent.discover(args.channel))
    elif args.command == "evaluate":
        _print(agent.evaluate())
    elif args.command == "plan":
        _print(agent.plan(args.channel))
    elif args.command == "execute":
        _print(await agent.execute(args.channel, live=args.live))
    elif args.command == "check-replies":
        _print(await agent.check_boss_replies(live_resume_send=args.send_resume))
    elif args.command == "check-receipts":
        _print(agent.check_receipts())
    elif args.command == "boss-login":
        connector = BossConnector(service.config.boss)
        try:
            _print((await connector.interactive_login(args.timeout)).to_dict())
        finally:
            await connector.close()
    elif args.command == "run-cycle":
        _print(await agent.run_cycle(live=args.live))
    return 0


def main(argv: Sequence[str] | None = None) -> None:
    raise SystemExit(asyncio.run(_run(build_parser().parse_args(argv))))


if __name__ == "__main__":
    main()
