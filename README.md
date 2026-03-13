# RAVEN Live Agent

RAVEN (Real-time Agent for Visual Emergency Navigation) is a multimodal incident response copilot.

It delivers a live voice + vision experience that goes beyond chat UI:
- real-time camera + microphone streaming
- low-latency bidirectional WebSocket interaction
- tool-calling for hazard checks and incident brief generation
- cloud-ready architecture on Google Cloud Run

## Origin Story

RAVEN is grounded in a real highway trauma moment:
traveling from Ekiti to Lagos after a family event, we encountered a violent storm and a major multi-vehicle incident involving a trailer, a nine-seater bus, and several cars.

That experience shaped the product thesis:
in severe weather and chaotic road conditions, people need a live, grounded copilot that helps them make safer decisions quickly.

Full narrative:
- [founder_story.md](/Users/surfiniaburger/Desktop/way-back-home/raven-live-agent/docs/founder_story.md)
- [submission_evidence_pack.md](/Users/surfiniaburger/Desktop/way-back-home/raven-live-agent/docs/submission_evidence_pack.md)
- [multiplatform_frontend_guide.md](/Users/surfiniaburger/Desktop/way-back-home/raven-live-agent/docs/multiplatform_frontend_guide.md)

## Hackathon Fit

- **Category:** Live Agents
- **Mandatory tech:** Gemini Live API / ADK, hosted on Google Cloud
- **Scoring alignment:**
  - Innovation & UX: live audio-video with interruption-ready flow
  - Technical execution: ADK runner, structured tools, robust stream loop
  - Demo quality: explicit proof of live software and cloud backend

## Repository Layout

```text
raven-live-agent/
  backend/
    app/
      agents/live_incident_agent.py
      tools/grounding_tools.py
      tools/risk_tools.py
      data/sop_catalog.json
      main.py
    requirements.txt
    pyproject.toml
  frontend/
    src/
      components/LiveOpsConsole.jsx
      hooks/useGeminiSocket.js
      hooks/audioStreamer.js
      hooks/audioRecorder.js
      App.jsx
      main.jsx
  docs/
    demo_script.md
  android/
    README.md
```

## What Was Reused

From existing `way-back-home` and ADK sample patterns:
- Level 3 live streaming transport loop (backend + WebSocket message contract)
- Level 3 frontend camera/mic stream hooks
- ADK Live agent instruction + tool-calling pattern

## Local Run

## 1. Backend

```bash
cd /Users/surfiniaburger/Desktop/way-back-home/raven-live-agent/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Choose one auth mode
# A) AI Studio
export GOOGLE_GENAI_USE_VERTEXAI=FALSE
export GOOGLE_API_KEY="YOUR_API_KEY"

# B) Vertex AI
# export GOOGLE_GENAI_USE_VERTEXAI=TRUE
# export GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
# export GOOGLE_CLOUD_LOCATION="us-central1"
# export ENABLE_BASIC_GUARDRAILS=true

uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Alternative if you are already inside `backend/app`:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

## 2. Frontend

```bash
cd /Users/surfiniaburger/Desktop/way-back-home/raven-live-agent/frontend
npm install
npm run dev
```

Open:
- `http://localhost:5173`

By default, frontend uses the same host for WebSocket. For local split-host testing, proxy or align host/port in Vite config.

For device/Capacitor testing, set explicit websocket base:

```bash
VITE_WS_BASE_URL=ws://<LAN_OR_PUBLIC_HOST>:8000 npm run dev
```

## 3. Android 

Android client lives in:

- `/Users/surfiniaburger/Desktop/way-back-home/raven-live-agent/android`

It supports direct phone camera + mic streaming to the same ADK WebSocket backend.
See mobile setup and backend URL config in:

- [Android README](/Users/surfiniaburger/Desktop/way-back-home/raven-live-agent/android/README.md)

## 4. Grounding With Vector Search 2.0

New modules added for scalable grounding:

- `backend/app/grounding/vector_store.py`
- `backend/app/tools/vector_grounding_tools.py`
- `backend/scripts/ingest_vector_data.py`
- `backend/data/sources/incident_knowledge.jsonl`

The current synthetic internal corpus is story-aligned to Nigerian highway storm incidents and first-response operations to support realistic demo grounding.

### Ingest sample corpus

```bash
cd /Users/surfiniaburger/Desktop/way-back-home/raven-live-agent/backend
source .venv/bin/activate
pip install -r requirements.txt

# Create backend .env first
cp .env.example .env

python scripts/ingest_vector_data.py \
  --input data/sources/incident_knowledge.jsonl \
  --batch-size 100
```

Validate corpus locally without cloud dependencies:

```bash
python scripts/ingest_vector_data.py \
  --input data/sources/incident_knowledge.jsonl \
  --dry-run
```

### Data quality references

- Source quality policy: [source_quality_policy.md](/Users/surfiniaburger/Desktop/way-back-home/raven-live-agent/docs/data/source_quality_policy.md)
- Authoritative source catalog starter: [authoritative_source_catalog.json](/Users/surfiniaburger/Desktop/way-back-home/raven-live-agent/backend/data/sources/authoritative_source_catalog.json)

## 4.1 Grounding Evaluation

Run confidence-gating evaluation:

```bash
cd /Users/surfiniaburger/Desktop/way-back-home/raven-live-agent/backend
source .venv/bin/activate

python eval/eval_grounding.py \
  --eval-set eval/data/grounding_eval_set.jsonl \
  --output eval/data/grounding_eval_report.json
```

This reports:
- pass rate against expected gating modes
- source coverage
- average confidence
- mode distribution (`grounded_answer_ok`, `answer_with_caution`, `ask_clarifying_or_abstain`, etc.)

If Vector Search is not yet provisioned, retrieval tools use a local JSONL fallback search so you can still test end-to-end behavior.

## Testing

Run backend unit tests (including ElevenLabs fallback harness):

```bash
cd /Users/surfiniaburger/Desktop/way-back-home/raven-standalone/backend
uv run pytest -q
```

### Agent grounding behavior

The live agent now has a vector retrieval tool:

- `search_incident_knowledge(query, jurisdiction, doc_type, limit)`

This is intended for policy/procedure/legal-sensitive guidance before final answer generation.

## 5. Cloud Run Deployment

Files added:

- `/Users/surfiniaburger/Desktop/way-back-home/raven-live-agent/cloudbuild.yaml`
- `/Users/surfiniaburger/Desktop/way-back-home/raven-live-agent/deploy_cloud_run.sh`
- `/Users/surfiniaburger/Desktop/way-back-home/raven-live-agent/.env.example`
- `/Users/surfiniaburger/Desktop/way-back-home/raven-live-agent/backend/.env.example`
- backend/frontend Dockerfiles

Deploy:

```bash
cd /Users/surfiniaburger/Desktop/way-back-home/raven-live-agent
cp .env.example .env
./deploy_cloud_run.sh
```

## Core Agent Behavior

Agent file: `backend/app/agents/live_incident_agent.py`

Current behavior:
- speaks concise operational responses
- calls `detect_hazard(scene_summary)` for risk classification
- calls `fetch_weather_context(jurisdiction, location, latitude, longitude, horizon_hours)` as the default weather router
- calls `fetch_nigeria_weather_advisory(location, horizon_hours)` for Nigeria weather advisory context
- calls `fetch_weather_alerts(latitude, longitude)` for local alert context
- calls `query_fema_incidents(state)` for regional incident grounding
- calls `search_sop_guidance(query)` for internal procedure grounding
- calls `generate_incident_brief(incident_notes, actions_taken)` for handoff output
- defaults to safety-first guidance for immediate danger
- includes `Sources:` when tool-grounded context is used

Note: `fetch_weather_context` is the guardrail entrypoint. For Nigeria demos, provide `jurisdiction=ng` and location context so routing stays on the NiMet advisory path; US weather/FEMA tools are still available for US-specific flows.

## Mar 7 Kickoff Status

Completed on **March 7, 2026**:
- project scaffold created (`raven-live-agent`)
- frontend live-streaming hooks copied from Level 3
- backend live WebSocket + ADK runner skeleton created
- initial agent and tools added
- submission docs drafted (`README.md`, `docs/demo_script.md`)

## Mar 8 Grounding Status

Completed on **March 8, 2026**:
- Added weather, FEMA, and SOP grounding tools.
- Added local SOP catalog seed data.
- Updated live agent instructions for explicit tool-grounding and citations output.

## Mar 9 Safety + UI Status

Completed on **March 9, 2026**:
- Added `BasicGuardrailsPlugin` for user/tool/model output safety checks.
- Wired plugins into ADK runner initialization.
- Updated frontend timeline to render discovered `Sources:` entries.

## Mar 10 Reliability Status

Completed on **March 10, 2026**:
- Added retry/backoff for weather and FEMA grounding HTTP calls.
- Added input validation for coordinates/state and structured tool error returns.
- Added backend WebSocket payload validation with system warning messages.
- Added frontend incident panel for hazard level, tags, brief summary/actions, and source count.
- Enabled `vectorsearch.googleapis.com` on `gem-creator` and validated ADC auth flow.
- Fixed Vector Search 2.0 SDK compatibility in `backend/app/grounding/vector_store.py`:
  - collection create payload shape
  - batch ingest request shape
  - hybrid search parsing (`distance` vs `score`)
  - weighted RRF request options
- Added API-compatible metadata filters in `backend/app/tools/vector_grounding_tools.py` and removed cloud fallback mode for valid in-domain queries.
- Rebuilt in-domain eval set and reran eval:
  - pass rate: `1.0` (5/5)
  - source coverage: `0.6`
  - report: `backend/eval/data/grounding_eval_report.json`

## Cloud Grounding Runbook

```bash
cd /Users/surfiniaburger/Desktop/way-back-home/raven-live-agent

# one-time API enable
gcloud services enable vectorsearch.googleapis.com --project gem-creator

# ingest
cd backend
set -a && source .env && set +a
.venv/bin/python scripts/ingest_vector_data.py --input data/sources/incident_knowledge.jsonl --batch-size 50

# eval
cd ..
set -a && source backend/.env && set +a
backend/.venv/bin/python backend/eval/eval_grounding.py
```

## Next Milestones

1. Add optional LLM-as-a-judge and/or Model Armor mode behind feature flags
2. Expand incident panel with explicit recommended actions and confidence
3. Deploy backend + frontend to Cloud Run and record cloud proof clip
4. Record final 4-minute demo and submit
