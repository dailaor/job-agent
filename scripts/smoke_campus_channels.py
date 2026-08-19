from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from job_agent.connectors.campus import CampusPortalConnector


async def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only live smoke test for built-in campus portals")
    parser.add_argument("--config", default="config.example.json")
    parser.add_argument("--keyword", default="产品经理")
    parser.add_argument("--channel", action="append", default=[], help="official site id; repeat to select several")
    args = parser.parse_args()

    data = json.loads(Path(args.config).read_text(encoding="utf-8"))
    selected = set(args.channel)
    definitions = [
        item for item in data.get("official_sites", [])
        if item.get("strategy") == "campus_api" and (not selected or item.get("id") in selected)
    ]
    if not definitions:
        print("No matching campus_api channels in config")
        return 2

    failures = 0
    for definition in definitions:
        started = time.perf_counter()
        try:
            jobs = await CampusPortalConnector(definition).discover([args.keyword])
            sample = " / ".join(job.title for job in jobs[:3]) or "no matching jobs"
            print(
                f"{definition['id']}: OK records={len(jobs)} "
                f"elapsed={time.perf_counter() - started:.2f}s sample={sample}"
            )
        except Exception as exc:
            failures += 1
            print(f"{definition.get('id', 'unknown')}: FAIL {type(exc).__name__}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
