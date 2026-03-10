"""Ingest JSONL knowledge records into Vertex AI Vector Search 2.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.grounding.vector_store import (
    ensure_collection,
    ingest_records,
    load_config_from_env,
)


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest vector grounding records.")
    parser.add_argument(
        "--input",
        default="backend/data/sources/incident_knowledge.jsonl",
        help="Path to JSONL records.",
    )
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and summarize records without calling Vector Search APIs.",
    )
    args = parser.parse_args()

    path = Path(args.input)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    rows = _load_jsonl(path)

    if not rows:
        print("No rows found in input.")
        return

    if args.dry_run:
        print(
            {
                "status": "dry_run_ok",
                "rows": len(rows),
                "sample_ids": [r.get("data_object_id", "") for r in rows[:5]],
            }
        )
        return

    config = load_config_from_env()

    result = ensure_collection(config)
    print(f"Collection status: {result}")

    ingest_result = ingest_records(config=config, records=rows, batch_size=args.batch_size)
    print(f"Ingest result: {ingest_result}")


if __name__ == "__main__":
    main()
