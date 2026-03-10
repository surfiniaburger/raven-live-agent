"""Vector Search 2.0 integration for incident knowledge grounding."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass
class VectorStoreConfig:
    project_id: str
    location: str
    collection_id: str
    vector_field: str = "content_embedding"

    @property
    def collection_path(self) -> str:
        return f"projects/{self.project_id}/locations/{self.location}/collections/{self.collection_id}"


class VectorStoreError(RuntimeError):
    """Raised when vector store calls fail."""


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _parse_iso_date(raw: str) -> date | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except Exception:  # noqa: BLE001
        try:
            return date.fromisoformat(raw[:10])
        except Exception:  # noqa: BLE001
            return None


def _source_quality(hit: dict[str, Any]) -> float:
    """Heuristic quality score for retrieval source ranking."""
    doc_type = (hit.get("doc_type", "") or "").lower()
    source_url = hit.get("source_url", "") or ""
    version = hit.get("version", "") or ""
    effective_date = hit.get("effective_date", "") or ""

    doc_type_weight = {
        "regulation": 0.95,
        "standard": 0.9,
        "sop": 0.88,
        "playbook": 0.82,
        "guideline": 0.78,
        "memo": 0.7,
    }
    quality = doc_type_weight.get(doc_type, 0.65)

    if source_url.startswith("https://"):
        quality += 0.05
    elif source_url.startswith("http://"):
        quality += 0.02

    if version:
        quality += 0.03

    parsed = _parse_iso_date(effective_date)
    if parsed:
        age_days = (date.today() - parsed).days
        if age_days <= 90:
            quality += 0.08
        elif age_days <= 365:
            quality += 0.05
        elif age_days <= 730:
            quality += 0.02

    return round(_clamp(quality), 4)


def _compute_confidence(ranked_hits: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute confidence + gating recommendation from ranked results."""
    if not ranked_hits:
        return {
            "overall": 0.0,
            "top_retrieval_score": 0.0,
            "top_source_quality": 0.0,
            "recommendation": "abstain_no_results",
            "reason": "No results returned from vector search.",
        }

    top = ranked_hits[0]
    top_rank = float(top.get("rank_score", 0.0))
    top_quality = float(top.get("source_quality", 0.0))

    second_rank = float(ranked_hits[1].get("rank_score", 0.0)) if len(ranked_hits) > 1 else 0.0
    rank_gap = max(0.0, top_rank - second_rank)
    avg_quality = sum(float(h.get("source_quality", 0.0)) for h in ranked_hits[:3]) / min(len(ranked_hits), 3)

    overall = _clamp(0.55 * top_rank + 0.2 * rank_gap + 0.25 * avg_quality)

    if overall >= 0.72 and top_quality >= 0.72:
        recommendation = "grounded_answer_ok"
        reason = "High confidence retrieval with strong source quality."
    elif overall >= 0.5:
        recommendation = "answer_with_caution"
        reason = "Moderate confidence. Include caveats and request confirmation."
    else:
        recommendation = "ask_clarifying_or_abstain"
        reason = "Low confidence retrieval. Ask clarifying question or abstain."

    return {
        "overall": round(overall, 4),
        "top_retrieval_score": round(top_rank, 4),
        "top_source_quality": round(top_quality, 4),
        "rank_gap": round(rank_gap, 4),
        "recommendation": recommendation,
        "reason": reason,
    }


def load_config_from_env() -> VectorStoreConfig:
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    collection_id = os.getenv("VECTOR_COLLECTION_ID", "raven-incident-knowledge")
    vector_field = os.getenv("VECTOR_FIELD", "content_embedding")

    if not project_id:
        raise VectorStoreError("GOOGLE_CLOUD_PROJECT is required for vector search.")

    return VectorStoreConfig(
        project_id=project_id,
        location=location,
        collection_id=collection_id,
        vector_field=vector_field,
    )


def _clients():
    """Lazy import vector search SDK to avoid hard runtime failure if package is absent."""
    try:
        from google.cloud import vectorsearch_v1beta  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise VectorStoreError(
            "google-cloud-vectorsearch is not installed. Add it to dependencies."
        ) from exc

    return (
        vectorsearch_v1beta,
        vectorsearch_v1beta.VectorSearchServiceClient(),
        vectorsearch_v1beta.DataObjectServiceClient(),
        vectorsearch_v1beta.DataObjectSearchServiceClient(),
    )


def ensure_collection(config: VectorStoreConfig) -> dict[str, Any]:
    """Create collection if missing with auto-embedding configuration."""
    vectorsearch_v1beta, admin_client, _, _ = _clients()

    collection_name = config.collection_path
    try:
        admin_client.get_collection(name=collection_name)
        return {"status": "exists", "collection": collection_name}
    except Exception:  # noqa: BLE001
        pass

    schema = {
        "data_schema": {
            "type": "object",
            "properties": {
                "doc_id": {"type": "string"},
                "title": {"type": "string"},
                "source_url": {"type": "string"},
                "doc_type": {"type": "string"},
                "jurisdiction": {"type": "string"},
                "effective_date": {"type": "string"},
                "version": {"type": "string"},
                "tags": {"type": "string"},
                "content": {"type": "string"},
            },
        },
        "vector_schema": {
            config.vector_field: {
                "dense_vector": {
                    "dimensions": 768,
                    "vertex_embedding_config": {
                        "model_id": "gemini-embedding-001",
                        "task_type": "RETRIEVAL_DOCUMENT",
                        "text_template": "Title: {title}. Type: {doc_type}. Content: {content}.",
                    },
                }
            }
        },
    }

    parent = f"projects/{config.project_id}/locations/{config.location}"
    request = vectorsearch_v1beta.CreateCollectionRequest(
        parent=parent,
        collection_id=config.collection_id,
        collection=schema,
    )
    op = admin_client.create_collection(request=request)
    op.result(timeout=900)
    return {"status": "created", "collection": collection_name}


def ingest_records(config: VectorStoreConfig, records: list[dict[str, Any]], batch_size: int = 100) -> dict[str, Any]:
    """Batch insert records as Data Objects and trigger auto-embedding."""
    vectorsearch_v1beta, _, data_client, _ = _clients()

    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        data_objects = []
        for item in batch:
            data_objects.append(
                vectorsearch_v1beta.DataObject(
                    data_object_id=item["data_object_id"],
                    data=item["data"],
                    vectors={},
                )
            )

        req = vectorsearch_v1beta.BatchCreateDataObjectsRequest(
            parent=config.collection_path,
            requests=[
                vectorsearch_v1beta.CreateDataObjectRequest(
                    parent=config.collection_path,
                    data_object_id=obj.data_object_id,
                    data_object=obj,
                )
                for obj in data_objects
            ],
        )
        data_client.batch_create_data_objects(request=req)
        total += len(batch)

    return {"ingested": total, "collection": config.collection_path}


def hybrid_search(
    config: VectorStoreConfig,
    query: str,
    limit: int = 5,
    metadata_filter: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run semantic + text hybrid search and return normalized results for tool responses."""
    vectorsearch_v1beta, _, _, search_client = _clients()

    output_fields = vectorsearch_v1beta.OutputFields(
        data_fields=[
            "doc_id",
            "title",
            "source_url",
            "doc_type",
            "jurisdiction",
            "effective_date",
            "version",
            "tags",
            "content",
        ]
    )

    semantic_kwargs = {
        "search_text": query,
        "search_field": config.vector_field,
        "top_k": limit,
        "task_type": "QUESTION_ANSWERING",
        "output_fields": output_fields,
    }
    text_kwargs = {
        "search_text": query,
        "data_field_names": ["title", "content", "tags", "doc_type", "jurisdiction"],
        "top_k": limit,
        "output_fields": output_fields,
    }
    if metadata_filter:
        semantic_kwargs["filter"] = metadata_filter
        text_kwargs["filter"] = metadata_filter

    semantic_search = vectorsearch_v1beta.SemanticSearch(**semantic_kwargs)
    text_search = vectorsearch_v1beta.TextSearch(**text_kwargs)

    req = vectorsearch_v1beta.BatchSearchDataObjectsRequest(
        parent=config.collection_path,
        searches=[
            vectorsearch_v1beta.Search(semantic_search=semantic_search),
            vectorsearch_v1beta.Search(text_search=text_search),
        ],
        combine=vectorsearch_v1beta.BatchSearchDataObjectsRequest.CombineResultsOptions(
            ranker=vectorsearch_v1beta.Ranker(
                rrf=vectorsearch_v1beta.ReciprocalRankFusion(weights=[0.6, 0.4]),
            )
        ),
    )

    resp = search_client.batch_search_data_objects(request=req)
    raw_hits = []

    first_result_list = []
    if getattr(resp, "results", None):
        first_result_list = list(resp.results[0].results)

    for ranked in first_result_list[:limit]:
        obj = ranked.data_object
        fields = dict(obj.data)
        raw_score = getattr(ranked, "score", None)
        if raw_score is None:
            distance = float(getattr(ranked, "distance", 1.0))
            raw_score = 1.0 / (1.0 + max(distance, 0.0))

        raw_hits.append(
            {
                "score": float(raw_score),
                "doc_id": fields.get("doc_id", ""),
                "title": fields.get("title", ""),
                "source_url": fields.get("source_url", ""),
                "doc_type": fields.get("doc_type", ""),
                "jurisdiction": fields.get("jurisdiction", ""),
                "effective_date": fields.get("effective_date", ""),
                "version": fields.get("version", ""),
                "tags": fields.get("tags", ""),
                "content": fields.get("content", ""),
            }
        )

    if not raw_hits:
        confidence = _compute_confidence([])
        return {
            "results": [],
            "sources": [],
            "confidence": confidence,
            "gating": {
                "should_abstain": True,
                "should_ask_clarifying": True,
            },
        }

    scores = [float(h.get("score", 0.0)) for h in raw_hits]
    min_score = min(scores)
    max_score = max(scores)
    score_range = max(max_score - min_score, 1e-9)

    ranked_hits = []
    for h in raw_hits:
        retrieval_norm = _clamp((float(h.get("score", 0.0)) - min_score) / score_range)
        quality = _source_quality(h)
        rank_score = _clamp(0.7 * retrieval_norm + 0.3 * quality)
        enriched = dict(h)
        enriched["retrieval_score_normalized"] = round(retrieval_norm, 4)
        enriched["source_quality"] = quality
        enriched["rank_score"] = round(rank_score, 4)
        ranked_hits.append(enriched)

    ranked_hits.sort(key=lambda x: x["rank_score"], reverse=True)
    confidence = _compute_confidence(ranked_hits)
    should_abstain = confidence["recommendation"] in {"abstain_no_results", "ask_clarifying_or_abstain"}
    should_ask_clarifying = confidence["recommendation"] in {"answer_with_caution", "ask_clarifying_or_abstain"}

    return {
        "results": ranked_hits,
        "sources": [
            {"id": h["doc_id"], "title": h["title"], "url": h["source_url"]}
            for h in ranked_hits
        ],
        "confidence": confidence,
        "gating": {
            "should_abstain": should_abstain,
            "should_ask_clarifying": should_ask_clarifying,
        },
    }
