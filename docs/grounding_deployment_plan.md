# Grounding + Deployment Plan

## Objective
Move RAVEN from direct-API-only grounding to a scalable hybrid grounding architecture:
- Vector Search 2.0 for stable knowledge corpora
- Live APIs for real-time volatile context
- ADK tool orchestration with citations

## Phase 1: Data Model and Corpus Readiness
1. Define schema fields: `doc_id,title,source_url,doc_type,jurisdiction,effective_date,version,tags,content`.
2. Curate initial corpus from internal SOP/playbooks + approved public safety guidance.
3. Apply legal/data checks:
   - license and attribution documented
   - no PII secrets in indexed text
   - provenance retained in `source_url`

## Phase 2: Ingestion and Indexing
1. Use `backend/scripts/ingest_vector_data.py` with JSONL records.
2. Create or reuse Vector Search 2.0 collection via `vector_store.ensure_collection`.
3. Batch ingest and trigger auto-embeddings with `gemini-embedding-001`.
4. Version data snapshots in source control or object storage.

## Phase 3: Retrieval and Agent Integration
1. Use `search_incident_knowledge` tool for policy/procedure guidance prompts.
2. Keep `fetch_weather_alerts` + `query_fema_incidents` for live context.
3. Enforce `Sources:` output block on grounded answers.
4. Apply confidence gates from tool output:
   - `confidence.overall`, `confidence.recommendation`
   - `gating.should_abstain`, `gating.should_ask_clarifying`
   - low confidence -> ask clarifying question or abstain
5. Prefer sources by quality-weighted rank (`rank_score`), not raw retrieval score alone.

## Phase 4: Deployment and Runtime
1. Build/deploy backend and frontend via `cloudbuild.yaml` and `deploy_cloud_run.sh`.
2. Inject frontend websocket base URL from deployed backend URL.
3. Configure env vars for model + vector collection + safety toggle.
4. Add Cloud Run min/max instances and request timeout tuning after load tests.

## Phase 5: Evaluation and Ops
1. Build eval set for incident prompts (grounded + adversarial + ambiguous).
2. Track metrics:
   - grounded answer rate
   - citation validity
   - hallucination/unsafe response rate
   - retrieval latency p95
3. Add scheduled re-ingest job for corpus updates.
4. Add cleanup script for old collections/index artifacts to control spend.
