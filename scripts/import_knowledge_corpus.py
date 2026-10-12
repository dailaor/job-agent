from __future__ import annotations

import argparse
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from job_agent.config import load_config
from job_agent.database import Database
from job_agent.knowledge.service import KnowledgeService


TARGET_COMPANIES = ("腾讯", "阿里", "美团", "快手", "百度")
EMPLOYMENT_TYPES = ("full_time", "internship")


def _load_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".jsonl":
        records = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        records = json.loads(text)
    if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
        raise ValueError("corpus must be a JSON array or JSONL objects")
    return records


def _validate_batch(records: list[dict[str, Any]], *, require_quota: bool) -> dict[str, Any]:
    seen: set[tuple[str, str]] = set()
    counts: Counter[tuple[str, str]] = Counter()
    errors: list[str] = []
    for index, record in enumerate(records, start=1):
        company = str(record.get("company") or "")
        employment_type = str(record.get("employment_type") or "")
        source = str(record.get("source") or "")
        url = str(record.get("url") or "")
        if company not in TARGET_COMPANIES:
            errors.append(f"record {index}: unsupported company {company!r}")
        if employment_type not in EMPLOYMENT_TYPES:
            errors.append(f"record {index}: employment_type must be full_time or internship")
        if source not in {"nowcoder", "xiaohongshu"}:
            errors.append(f"record {index}: source must be nowcoder or xiaohongshu")
        key = (source, url)
        if key in seen:
            errors.append(f"record {index}: duplicate source URL")
        seen.add(key)
        counts[(company, employment_type)] += 1
    if require_quota:
        for company in TARGET_COMPANIES:
            for employment_type in EMPLOYMENT_TYPES:
                actual = counts[(company, employment_type)]
                if actual != 5:
                    errors.append(
                        f"quota {company}/{employment_type}: expected 5, got {actual}"
                    )
    if errors:
        raise ValueError("\n".join(errors))
    return {
        company: {employment_type: counts[(company, employment_type)] for employment_type in EMPLOYMENT_TYPES}
        for company in TARGET_COMPANIES
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and import a reviewed job-intelligence corpus")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--database", default=".job-agent/job-agent.sqlite3")
    parser.add_argument("--file", required=True)
    parser.add_argument("--require-quota", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", help="Optional UTF-8 JSON report path")
    args = parser.parse_args()

    records = _load_records(Path(args.file))
    quota = _validate_batch(records, require_quota=args.require_quota)
    config = load_config(args.config)
    temporary: tempfile.TemporaryDirectory[str] | None = None
    database_path = Path(args.database)
    if args.dry_run:
        temporary = tempfile.TemporaryDirectory()
        database_path = Path(temporary.name) / "dry-run.sqlite3"
    service = KnowledgeService(config.knowledge, Database(database_path))

    results: list[dict[str, Any]] = []
    for record in records:
        result = service.import_payload(record)
        results.append({
            "source": record.get("source"),
            "url": record.get("url"),
            "company": result.get("company"),
            "employment_type": result.get("employment_type"),
            "status": result.get("status"),
            "quality_score": result.get("quality_score"),
            "chunks": result.get("chunks"),
            "reasons": result.get("reasons"),
        })
    status_counts = Counter(str(result["status"]) for result in results)
    output = {
        "dry_run": args.dry_run,
        "records": len(records),
        "quota": quota,
        "statuses": dict(status_counts),
        "accepted": sum(1 for result in results if result["status"] == "accepted"),
        "all_accepted": all(result["status"] == "accepted" for result in results),
        "results": results,
    }
    rendered = json.dumps(output, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    print(rendered)
    if temporary is not None:
        temporary.cleanup()
    if args.require_quota and not output["all_accepted"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
