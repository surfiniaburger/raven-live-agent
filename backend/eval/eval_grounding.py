"""Evaluate retrieval gating behavior and citation quality for RAVEN grounding."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.tools.vector_grounding_tools import search_incident_knowledge


@dataclass
class EvalCase:
    id: str
    query: str
    expected_mode: str  # grounded_answer_ok | answer_with_caution | ask_clarifying_or_abstain | below_min_confidence | abstain_no_results
    jurisdiction: str = ""
    doc_type: str = ""
    min_confidence: float = 0.55


@dataclass
class EvalResult:
    id: str
    expected_mode: str
    actual_mode: str
    passed: bool
    confidence: float
    source_count: int
    error: str = ""


def load_eval_set(path: Path) -> list[EvalCase]:
    rows: list[EvalCase] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            rows.append(
                EvalCase(
                    id=raw["id"],
                    query=raw["query"],
                    expected_mode=raw["expected_mode"],
                    jurisdiction=raw.get("jurisdiction", ""),
                    doc_type=raw.get("doc_type", ""),
                    min_confidence=float(raw.get("min_confidence", 0.55)),
                )
            )
    return rows


def evaluate_case(case: EvalCase) -> EvalResult:
    response = search_incident_knowledge(
        query=case.query,
        jurisdiction=case.jurisdiction,
        doc_type=case.doc_type,
        limit=5,
        min_confidence=case.min_confidence,
    )

    if response.get("error"):
        return EvalResult(
            id=case.id,
            expected_mode=case.expected_mode,
            actual_mode="error",
            passed=False,
            confidence=0.0,
            source_count=0,
            error=response["error"],
        )

    confidence = float(response.get("confidence", {}).get("overall", 0.0))
    actual_mode = response.get("confidence", {}).get("recommendation", "unknown")
    source_count = len(response.get("sources", []))

    return EvalResult(
        id=case.id,
        expected_mode=case.expected_mode,
        actual_mode=actual_mode,
        passed=actual_mode == case.expected_mode,
        confidence=confidence,
        source_count=source_count,
    )


def summarize(results: list[EvalResult]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    errors = sum(1 for r in results if r.actual_mode == "error")
    with_sources = sum(1 for r in results if r.source_count > 0)

    mode_counts: dict[str, int] = {}
    for r in results:
        mode_counts[r.actual_mode] = mode_counts.get(r.actual_mode, 0) + 1

    avg_conf = round(sum(r.confidence for r in results) / total, 4) if total else 0.0

    return {
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "errors": errors,
        "source_coverage": round(with_sources / total, 4) if total else 0.0,
        "avg_confidence": avg_conf,
        "mode_counts": mode_counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate RAVEN grounding confidence gating.")
    parser.add_argument(
        "--eval-set",
        default="backend/eval/data/grounding_eval_set.jsonl",
        help="Path to JSONL eval set.",
    )
    parser.add_argument(
        "--output",
        default="backend/eval/data/grounding_eval_report.json",
        help="Where to write JSON report.",
    )
    args = parser.parse_args()

    eval_path = Path(args.eval_set)
    if not eval_path.exists():
        raise FileNotFoundError(f"Eval set not found: {eval_path}")

    cases = load_eval_set(eval_path)
    results = [evaluate_case(case) for case in cases]
    summary = summarize(results)

    payload = {
        "summary": summary,
        "results": [r.__dict__ for r in results],
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print(f"Report written: {out_path}")


if __name__ == "__main__":
    main()
