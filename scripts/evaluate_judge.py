from __future__ import annotations

import argparse
import json
import sqlite3
import tempfile
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from job_agent.config import load_config
from job_agent.database import Database
from job_agent.knowledge.models import EvidenceBundle
from job_agent.knowledge.service import KnowledgeService
from job_agent.models import Job
from job_agent.scoring import DeepSeekScoringPort, RuleScoringPort


def _clone_database(source: Path, target: Path) -> None:
    with sqlite3.connect(source) as source_connection, sqlite3.connect(target) as target_connection:
        source_connection.backup(target_connection)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _load_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        cases = payload
        defaults: dict[str, Any] = {}
    elif isinstance(payload, dict):
        defaults = payload.get("defaults", {})
        cases = payload.get("cases")
        if not isinstance(defaults, dict):
            raise ValueError("benchmark.defaults must be an object")
    else:
        raise ValueError("benchmark must be an array or a versioned benchmark object")
    if not isinstance(cases, list) or not all(isinstance(item, dict) for item in cases):
        raise ValueError("benchmark cases must be an array of objects")
    merged = [_deep_merge(defaults, item) for item in cases]
    identifiers = [str(item.get("id", "")).strip() for item in merged]
    if any(not identifier for identifier in identifiers) or len(set(identifiers)) != len(identifiers):
        raise ValueError("benchmark case ids must be non-empty and unique")
    for case in merged:
        if not isinstance(case.get("job"), dict) or not isinstance(case.get("expected"), dict):
            raise ValueError(f"benchmark case {case['id']} must contain job and expected objects")
        expected = case["expected"]
        for key in ("strategy", "ability_relation", "need_score_range"):
            if key not in expected:
                raise ValueError(f"benchmark case {case['id']} is missing expected.{key}")
    return merged


def _config_for_case(config: Any, case: dict[str, Any]) -> Any:
    case_config = deepcopy(config)
    for section_name in ("candidate", "preferences"):
        overrides = case.get(section_name, {})
        if not isinstance(overrides, dict):
            raise ValueError(f"case {section_name} override must be an object")
        section = getattr(case_config, section_name)
        for key, value in overrides.items():
            if not hasattr(section, key):
                raise ValueError(f"case contains unknown {section_name} field: {key}")
            setattr(section, key, value)
    case_config.validate()
    return case_config


def _score_case(evaluation: dict[str, Any], expected: dict[str, Any]) -> dict[str, bool]:
    checks = {
        "strategy": evaluation["strategy"] == expected["strategy"],
        "ability_relation": evaluation["ability_relation"] == expected["ability_relation"],
    }
    need_range = expected.get("need_score_range")
    if isinstance(need_range, list) and len(need_range) == 2:
        checks["need_band"] = float(need_range[0]) <= evaluation["need_score"] <= float(need_range[1])
    return checks


def _retrieval_leaks(bundle: EvidenceBundle) -> bool:
    return any(
        item.employment_type != bundle.employment_type
        for item in [*bundle.ability, *bundle.need]
    )


def _accuracy(checks: list[dict[str, bool]], key: str) -> float | None:
    values = [row[key] for row in checks if key in row]
    return round(sum(values) / len(values), 4) if values else None


def _check_accuracy(result: dict[str, Any]) -> float | None:
    checks = result.get("checks")
    if not isinstance(checks, dict) or not checks:
        return None
    values = [bool(checks[key]) for key in ("strategy", "ability_relation", "need_band") if key in checks]
    return sum(values) / len(values)


def _delta(after: object, before: object) -> float | None:
    if not isinstance(after, (int, float)) or not isinstance(before, (int, float)):
        return None
    return round(float(after) - float(before), 4)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pair the same DeepSeek Judge without and with RAG; rule scoring is secondary",
    )
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--database", default=".job-agent/job-agent.sqlite3")
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--provider", choices=["rule", "deepseek", "both"], default="both")
    parser.add_argument("--order-check", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()

    config = load_config(args.config)
    cases = _load_cases(Path(args.benchmark))
    with tempfile.TemporaryDirectory() as directory:
        cloned_path = Path(directory) / "judge-eval.sqlite3"
        _clone_database(Path(args.database), cloned_path)
        database = Database(cloned_path)
        knowledge = KnowledgeService(config.knowledge, database)
        scorers: dict[str, tuple[Any, str]] = {}
        if args.provider in {"rule", "both"}:
            scorers["rule"] = (RuleScoringPort(), "no_rag")
        if args.provider in {"deepseek", "both"}:
            scorers["deepseek_no_rag"] = (DeepSeekScoringPort(config.scoring), "no_rag")
            scorers["deepseek_rag"] = (DeepSeekScoringPort(config.scoring), "rag")

        records: list[dict[str, Any]] = []
        for index, case in enumerate(cases, start=1):
            case_config = _config_for_case(config, case)
            job_payload = dict(case["job"])
            job_payload.setdefault("source", "benchmark")
            job_payload.setdefault("source_id", f"judge-case-{index}")
            job_payload.setdefault("url", f"https://benchmark.invalid/jobs/{case['id']}")
            job = Job(**job_payload)
            job.id = database.upsert_job(job)[0]
            bundle = knowledge.retrieve_for_job(job, case_config)
            row: dict[str, Any] = {
                "id": case.get("id", index),
                "expected": case["expected"],
                "employment_type": bundle.employment_type,
                "evidence_count": bundle.evidence_count,
                "employment_leak": _retrieval_leaks(bundle),
                "coverage": bundle.coverage,
                "tags": case.get("tags", []),
                "gold_rationale": case.get("gold_rationale", ""),
                "results": {},
            }
            for name, (scorer, evidence_mode) in scorers.items():
                try:
                    evidence_input = bundle if evidence_mode == "rag" else None
                    evaluation = scorer.score(job, case_config, evidence_input)
                    result = evaluation.to_dict()
                    result["valid"] = True
                    result["evidence_mode"] = evidence_mode
                    if isinstance(scorer, DeepSeekScoringPort):
                        result["diagnostics"] = dict(scorer.last_diagnostics)
                    result["checks"] = _score_case(result, case["expected"])
                    if name == "deepseek_no_rag":
                        result["checks"]["no_rag_need_abstention"] = (
                            result.get("diagnostics", {}).get("need_insufficient_evidence") is True
                        )
                    if name == "deepseek_rag":
                        minimum_citations = int(case["expected"].get("minimum_rag_citations", 0))
                        minimum_ability_citations = int(
                            case["expected"].get("minimum_rag_ability_citations", 0)
                        )
                        minimum_need_citations = int(
                            case["expected"].get("minimum_rag_need_citations", 0)
                        )
                        diagnostics = result.get("diagnostics", {})
                        ability_citations = diagnostics.get("ability_citations", [])
                        need_citations = diagnostics.get("need_citations", [])
                        if minimum_citations:
                            citations = [*ability_citations, *need_citations]
                            result["checks"]["rag_citation"] = len(set(citations)) >= minimum_citations
                        if minimum_ability_citations:
                            result["checks"]["rag_ability_citation"] = (
                                len(set(ability_citations)) >= minimum_ability_citations
                            )
                        if minimum_need_citations:
                            result["checks"]["rag_need_citation"] = (
                                len(set(need_citations)) >= minimum_need_citations
                                and diagnostics.get("need_insufficient_evidence") is False
                            )
                    if name == "deepseek_rag" and args.order_check:
                        reversed_bundle = deepcopy(bundle)
                        reversed_bundle.ability.reverse()
                        reversed_bundle.need.reverse()
                        try:
                            reversed_evaluation = scorer.score(job, case_config, reversed_bundle)
                            result["order_check"] = {
                                "valid": True,
                                "strategy_same": reversed_evaluation.strategy == evaluation.strategy,
                                "ability_relation_same": (
                                    reversed_evaluation.ability_relation == evaluation.ability_relation
                                ),
                                "match_score_delta": round(
                                    abs(reversed_evaluation.match_score - evaluation.match_score), 2
                                ),
                                "need_score_delta": round(
                                    abs(reversed_evaluation.need_score - evaluation.need_score), 2
                                ),
                            }
                        except Exception as exc:
                            result["order_check"] = {
                                "valid": False,
                                "error": f"{type(exc).__name__}: {exc}",
                            }
                except Exception as exc:
                    result = {"valid": False, "error": f"{type(exc).__name__}: {exc}"}
                row["results"][name] = result
            records.append(row)

    metrics: dict[str, Any] = {
        "cases": len(records),
        "retrieval_employment_leaks": sum(bool(row["employment_leak"]) for row in records),
        "retrieval_zero_evidence_cases": sum(row["evidence_count"] == 0 for row in records),
        "retrieval_mean_evidence_count": round(
            sum(row["evidence_count"] for row in records) / max(1, len(records)), 2
        ),
        "retrieval_confidence": dict(Counter(
            str(row["coverage"].get("confidence", "unknown")) for row in records
        )),
        "providers": {},
    }
    for name in scorers:
        provider_rows = [row["results"][name] for row in records]
        valid_rows = [row for row in provider_rows if row.get("valid")]
        checks = [row["checks"] for row in valid_rows]
        provider_metrics: dict[str, Any] = {
            "valid_rate": round(len(valid_rows) / max(1, len(provider_rows)), 4),
            "strategy_accuracy": _accuracy(checks, "strategy"),
            "ability_relation_accuracy": _accuracy(checks, "ability_relation"),
            "need_band_accuracy": _accuracy(checks, "need_band"),
            "rag_citation_compliance": _accuracy(checks, "rag_citation"),
            "rag_ability_citation_compliance": _accuracy(checks, "rag_ability_citation"),
            "rag_need_citation_compliance": _accuracy(checks, "rag_need_citation"),
            "no_rag_need_abstention_rate": _accuracy(checks, "no_rag_need_abstention"),
            "judge_abstention_rate": (
                round(
                    sum(row.get("diagnostics", {}).get("judge_abstained") is True for row in valid_rows)
                    / len(valid_rows),
                    4,
                ) if valid_rows and name.startswith("deepseek") else None
            ),
            "errors": dict(Counter(row.get("error", "") for row in provider_rows if not row.get("valid"))),
        }
        if name == "deepseek_rag" and args.order_check:
            attempted_order_rows = [row["order_check"] for row in valid_rows if "order_check" in row]
            order_rows = [row for row in attempted_order_rows if row.get("valid")]
            provider_metrics["order_stability"] = {
                "valid_rate": round(
                    len(order_rows) / max(1, len(attempted_order_rows)), 4
                ),
                "strategy_same_rate": round(
                    sum(row["strategy_same"] for row in order_rows) / max(1, len(order_rows)), 4
                ),
                "ability_relation_same_rate": round(
                    sum(row["ability_relation_same"] for row in order_rows) / max(1, len(order_rows)), 4
                ),
                "mean_match_score_delta": round(
                    sum(row["match_score_delta"] for row in order_rows) / max(1, len(order_rows)), 2
                ),
                "mean_need_score_delta": round(
                    sum(row["need_score_delta"] for row in order_rows) / max(1, len(order_rows)), 2
                ),
                "errors": dict(Counter(
                    row.get("error", "") for row in attempted_order_rows if not row.get("valid")
                )),
            }
        metrics["providers"][name] = provider_metrics

    if {"deepseek_no_rag", "deepseek_rag"}.issubset(scorers):
        pairs = [
            (row["results"]["deepseek_no_rag"], row["results"]["deepseek_rag"])
            for row in records
            if row["results"]["deepseek_no_rag"].get("valid")
            and row["results"]["deepseek_rag"].get("valid")
        ]
        pair_scores = [
            (_check_accuracy(before), _check_accuracy(after)) for before, after in pairs
        ]
        comparable = [
            (before, after) for before, after in pair_scores
            if before is not None and after is not None
        ]
        no_rag_metrics = metrics["providers"]["deepseek_no_rag"]
        rag_metrics = metrics["providers"]["deepseek_rag"]
        metrics["rag_lift"] = {
            "valid_pairs": len(pairs),
            "strategy_accuracy_delta": _delta(
                rag_metrics["strategy_accuracy"], no_rag_metrics["strategy_accuracy"],
            ),
            "ability_relation_accuracy_delta": _delta(
                rag_metrics["ability_relation_accuracy"],
                no_rag_metrics["ability_relation_accuracy"],
            ),
            "need_band_accuracy_delta": _delta(
                rag_metrics["need_band_accuracy"], no_rag_metrics["need_band_accuracy"],
            ),
            "mean_check_accuracy_delta": (
                round(sum(after - before for before, after in comparable) / len(comparable), 4)
                if comparable else None
            ),
            "rag_wins": sum(after > before for before, after in comparable),
            "ties": sum(after == before for before, after in comparable),
            "rag_losses": sum(after < before for before, after in comparable),
            "strategy_change_rate": (
                round(
                    sum(before["strategy"] != after["strategy"] for before, after in pairs)
                    / len(pairs),
                    4,
                ) if pairs else None
            ),
        }

    output = {"metrics": metrics, "records": records}
    rendered = json.dumps(output, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
