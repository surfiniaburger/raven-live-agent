# Devpost Submission Draft (Final Form Order)

Copy this into Devpost fields in order.

## Project Name

RAVEN Live Agent

## Tagline

Real-time camera + voice incident copilot with grounded, confidence-gated response.

## Category

Live Agents

## Elevator Pitch

RAVEN is a multimodal live incident-response agent built with Gemini Live + ADK on Google Cloud Run. It streams camera and microphone in real time, handles interruption naturally, and returns grounded safety guidance with source evidence. It was inspired by a real highway storm collision on the Ekiti-Lagos corridor.

## Problem

In severe weather and roadside incidents, decision windows are short and stress is high. Standard chat interfaces are too slow and too detached from real-world context. Users need an assistant that can see, hear, adapt to interruption, and provide safe, grounded actions without hallucinated certainty.

## Solution

RAVEN provides a live operational copilot experience:

- Continuous audio + video input over WebSocket
- ADK-based live agent orchestration
- Tool-calling for hazard and incident-brief workflows
- Vector-grounded retrieval with confidence gating
- Source-quality ranking and abstain behavior for risky queries

This design prioritizes reliability under pressure: answer decisively when confidence is high, and degrade safely when confidence is low.

## Key Features

1. Live multimodal interaction (camera + microphone)
2. Interruption handling (barge-in) with context retention
3. Grounded SOP response with source citations
4. Legal-overreach and low-confidence abstain/clarify gates
5. Structured incident brief generation for handoff

## Built With

Gemini Live API, Google ADK, FastAPI, Python, React, WebSocket, Vertex AI Vector Search 2.0, Google Cloud Run

## Architecture Summary

Frontend (web/mobile) streams voice + camera to a FastAPI WebSocket gateway.  
The ADK live agent orchestrates tool calls for risk workflows and vector grounding.  
Grounding retrieval runs through Vertex AI Vector Search 2.0 collection `raven-incident-knowledge`.  
Responses return with confidence recommendation and source references.  
Backend is deployed on Cloud Run for managed scale and reliability.

## How to Run

```bash
cd /Users/surfiniaburger/Desktop/way-back-home/raven-live-agent/backend
set -a && source .env && set +a
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

```bash
cd /Users/surfiniaburger/Desktop/way-back-home/raven-live-agent/frontend
npm install
npm run dev
```

## Grounding Ingest + Eval

```bash
cd /Users/surfiniaburger/Desktop/way-back-home/raven-live-agent
gcloud services enable vectorsearch.googleapis.com --project gem-creator

cd backend
set -a && source .env && set +a
.venv/bin/python scripts/ingest_vector_data.py --input data/sources/incident_knowledge.jsonl --batch-size 50

cd ..
set -a && source backend/.env && set +a
backend/.venv/bin/python backend/eval/eval_grounding.py
```

Current eval report (`backend/eval/data/grounding_eval_report.json`):

- total: 5
- passed: 5
- pass_rate: 1.0
- errors: 0
- source_coverage: 0.6
- mode_counts:
  - grounded_answer_ok: 3
  - below_min_confidence: 1
  - ask_clarifying_or_abstain: 1

## Google Cloud Proof

Demo includes:

1. Cloud Run deployed service and active revision
2. Live request logs during session
3. Vector Search collection and ingest run
4. End-to-end eval execution

## Challenges We Ran Into

- Vector Search SDK/API shape differences (`data_objects` vs `requests`, `score` vs `distance`)
- API enablement and ADC quota-project setup
- Retrieval filter format compatibility
- Tuning confidence gating to avoid false certainty

## Accomplishments We’re Proud Of

- Broke out of text-box UX into live, interruptible multimodal interaction
- Added confidence-gated grounded response with explicit source handling
- Delivered cloud-deployed, reproducible ingest/eval pipeline
- Built a story-grounded product thesis with startup potential

## What We Learned

- Retrieval infrastructure details strongly affect agent reliability
- Safe abstention behavior is essential for incident-critical UX
- Judges respond best to measurable behavior plus cloud proof, not claims

## What’s Next

1. Expand authoritative per-jurisdiction corpus and policy packs
2. Add continuous ingestion and data quality monitoring
3. Add broader scenario evals and regression checks
4. Pilot with transport and emergency operations teams

## Links to Include in Devpost

- Repository URL: `<your public repo URL>`
- Demo Video URL: `<YouTube or Vimeo URL>`
- Cloud proof clip URL: `<public URL or repo file link>`
- Architecture diagram URL/file: `docs/submission_evidence_pack.md`
