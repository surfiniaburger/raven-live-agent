"""ADK tool wrappers around Vector Search 2.0 retrieval."""

from __future__ import annotations

import json
from pathlib import Path

try:
    from app.grounding.vector_store import (
        VectorStoreError,
        hybrid_search,
        load_config_from_env,
    )
except ModuleNotFoundError:
    from grounding.vector_store import (
        VectorStoreError,
        hybrid_search,
        load_config_from_env,
    )


def _local_fallback_search(query: str, limit: int = 5) -> dict:
    """Fallback lexical search against local JSONL corpus when vector service is unavailable."""
    root = Path(__file__).resolve().parents[2]
    local_path = root / "data" / "sources" / "incident_knowledge.jsonl"
    if not local_path.exists():
        return {
            "results": [],
            "sources": [],
            "confidence": {
                "overall": 0.0,
                "recommendation": "abstain_no_results",
                "reason": "Local fallback corpus missing.",
            },
            "gating": {"should_abstain": True, "should_ask_clarifying": True},
            "fallback_mode": True,
        }

    query_tokens = {tok for tok in query.lower().split() if len(tok) > 2}
    rows = []
    with local_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            data = obj.get("data", {})
            text = f"{data.get('title', '')} {data.get('content', '')} {data.get('tags', '')}".lower()
            overlap = sum(1 for tok in query_tokens if tok in text)
            if overlap == 0:
                continue
            score = min(1.0, overlap / max(len(query_tokens), 1))
            rows.append(
                {
                    "score": round(score, 4),
                    "doc_id": data.get("doc_id", obj.get("data_object_id", "")),
                    "title": data.get("title", ""),
                    "source_url": data.get("source_url", ""),
                    "doc_type": data.get("doc_type", ""),
                    "jurisdiction": data.get("jurisdiction", ""),
                    "effective_date": data.get("effective_date", ""),
                    "version": data.get("version", ""),
                    "tags": data.get("tags", ""),
                    "content": data.get("content", ""),
                    "retrieval_score_normalized": round(score, 4),
                    "source_quality": 0.72,
                    "rank_score": round(0.7 * score + 0.3 * 0.72, 4),
                }
            )

    rows.sort(key=lambda x: x["rank_score"], reverse=True)
    rows = rows[: max(1, min(limit, 10))]
    if not rows:
        return {
            "results": [],
            "sources": [],
            "confidence": {
                "overall": 0.0,
                "recommendation": "abstain_no_results",
                "reason": "No local fallback match.",
            },
            "gating": {"should_abstain": True, "should_ask_clarifying": True},
            "fallback_mode": True,
        }

    top = rows[0]
    overall = min(1.0, 0.6 * top["rank_score"] + 0.4 * top["source_quality"])
    recommendation = "grounded_answer_ok" if overall >= 0.72 else "answer_with_caution"
    return {
        "results": rows,
        "sources": [{"id": r["doc_id"], "title": r["title"], "url": r["source_url"]} for r in rows],
        "confidence": {
            "overall": round(overall, 4),
            "top_retrieval_score": top["rank_score"],
            "top_source_quality": top["source_quality"],
            "recommendation": recommendation,
            "reason": "Local fallback lexical retrieval.",
        },
        "gating": {
            "should_abstain": recommendation != "grounded_answer_ok",
            "should_ask_clarifying": recommendation != "grounded_answer_ok",
        },
        "fallback_mode": True,
    }


def search_incident_knowledge(
    query: str,
    jurisdiction: str = "",
    doc_type: str = "",
    limit: int = 5,
    min_confidence: float = 0.55,
) -> dict:
    """Search ingested incident corpus with hybrid semantic + keyword retrieval.

    Args:
        query: Incident grounding query.
        jurisdiction: Optional metadata filter (e.g., "us", "global").
        doc_type: Optional metadata filter (e.g., "SOP", "Playbook").
        limit: Max number of results.
        min_confidence: Confidence threshold for definitive grounded responses.
    """
    if not query.strip():
        return {"results": [], "sources": [], "error": "query is required"}
    lower_query = query.lower().strip()

    # Hard safety gate: prevent definitive legal/compliance claims across broad jurisdictions.
    legal_overreach_markers = [
        "legally binding",
        "all countries",
        "global legal ruling",
        "regulatory ruling",
    ]
    if any(m in lower_query for m in legal_overreach_markers):
        return {
            "results": [],
            "sources": [],
            "confidence": {
                "overall": 0.1,
                "recommendation": "ask_clarifying_or_abstain",
                "reason": "Query requests a broad legal ruling beyond safe grounded scope.",
            },
            "gating": {"should_abstain": True, "should_ask_clarifying": True},
            "fallback_mode": False,
        }

    # Ambiguity gate: very short queries should force clarification before definitive guidance.
    token_count = len([t for t in lower_query.split() if len(t) > 2])
    if token_count < 4:
        return {
            "results": [],
            "sources": [],
            "confidence": {
                "overall": 0.2,
                "recommendation": "ask_clarifying_or_abstain",
                "reason": "Query lacks enough context for reliable grounded action guidance.",
            },
            "gating": {"should_abstain": True, "should_ask_clarifying": True},
            "fallback_mode": False,
        }

    clauses = []
    if jurisdiction.strip():
        clauses.append({"jurisdiction": {"$eq": jurisdiction.strip()}})
    if doc_type.strip():
        clauses.append({"doc_type": {"$eq": doc_type.strip()}})

    metadata_filter = None
    if len(clauses) == 1:
        metadata_filter = clauses[0]
    elif len(clauses) > 1:
        metadata_filter = {"$and": clauses}

    try:
        cfg = load_config_from_env()
        result = hybrid_search(
            config=cfg,
            query=query,
            limit=max(1, min(limit, 10)),
            metadata_filter=metadata_filter,
        )
        confidence = result.get("confidence", {})
        overall = float(confidence.get("overall", 0.0))
        if overall < max(0.0, min(min_confidence, 1.0)):
            gating = result.get("gating", {})
            gating["should_abstain"] = True
            gating["should_ask_clarifying"] = True
            result["gating"] = gating
            confidence["recommendation"] = "below_min_confidence"
            confidence["reason"] = (
                f"Overall confidence {overall:.2f} below threshold {min_confidence:.2f}."
            )
            result["confidence"] = confidence
        return result
    except VectorStoreError as exc:
        fallback = _local_fallback_search(query=query, limit=limit)
        fallback["warning"] = f"vector_store_error: {exc}"
        return fallback
    except Exception as exc:  # noqa: BLE001
        fallback = _local_fallback_search(query=query, limit=limit)
        fallback["warning"] = f"vector_search_failed: {exc}"
        return fallback
