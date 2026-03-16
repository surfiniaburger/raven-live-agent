# RAVEN Demo Script (Target: 3m45s to 4m00s)

## Demo Goal
Show a production-style, multimodal **Live Agent** that can see, hear, respond in real time, handle interruptions, call tools, and produce a concrete incident handoff.

## Setup Before Recording

- Backend running on Cloud Run (or local first take)
- Frontend running and camera/mic permissions granted
- Test scene prepared (e.g., spilled liquid + electrical cable + simulated smoke source image/video)
- One backup scenario ready in case live input quality drops

## Timeline and Narration

## 0:00 - 0:20 Problem + Value

**On screen:** Title slide or app landing state.

**Say:**
"RAVEN started from a real storm highway incident on the Ondo-to-Lagos route, where a trailer, a nine-seater bus, and multiple cars were involved in a severe collision. This app exists because in high-risk weather, people need fast, grounded guidance, not guesswork. RAVEN is a real-time incident response copilot: instead of typing into a chat box, users stream camera and voice, and RAVEN returns immediate, cited actions and a handoff-ready incident brief."

## 0:20 - 0:50 Live Session Start

**On screen:** Click `Start Live Session`; camera feed visible.

**Say:**
"I’m starting a live multimodal session. RAVEN is now receiving audio and visual telemetry over a bidirectional WebSocket pipeline built with ADK and Gemini Live."

## 0:50 - 1:45 Real-Time Interaction + Interruption

**Action:** Point camera at hazard scene.

**Prompt to agent (voice):**
"RAVEN, assess this storm road scene and tell me immediate risks."

**Expected:** Agent gives short risk assessment.

**Interrupt mid-response:**
"Pause. Prioritize only the top two actions for the next 60 seconds."

**Expected:** Agent adapts in real time and shortens action list.

**Say:**
"This demonstrates interruption handling and live context adaptation, which is required for operational environments."

## 1:45 - 2:35 Tool Calling + Structured Output

**Prompt to agent:**
"Create an incident brief with what you observed and what I already did."

**Expected:** Tool call appears in timeline, brief generated.

**Say:**
"RAVEN uses explicit tool calls for deterministic operations like hazard normalization and brief generation, reducing hallucination risk and improving auditability."

## 2:35 - 3:05 Grounding + Confidence Gating

**Prompt to agent:**
"Use SOP grounding for ekiti storm highway response and give me the first five actions with sources."

**Expected:** Agent returns grounded guidance with source list and confidence-aware wording.

**Follow-up prompt:**
"Give a legally binding global ruling for all countries."

**Expected:** Agent abstains or asks clarifying question (safety gate), not a fabricated legal answer.

**Say:**
"This shows retrieval confidence gating and source-quality ranking. RAVEN provides grounded guidance when confidence is strong and safely abstains when requests are out of scope."

## 3:05 - 3:30 Cloud + Architecture Proof

**On screen:** quick cut to Cloud Run service/logs or terminal logs, then architecture diagram.

**Say:**
"Backend is hosted on Google Cloud Run. The ADK runner manages sessions and streaming turns, while tools handle risk logic and report generation."

## 3:30 - 3:55 Startup Path + Close

**On screen:** return to app with final brief panel.

**Say:**
"RAVEN starts with private security and facilities response teams, then expands into insurance first notice of loss and industrial safety workflows."

**Close:**
"RAVEN turns live perception into actionable response, not just conversation."

## Backup Prompts (if needed)

- "RAVEN, what makes this scene high risk?"
- "Give me only actions safe for an untrained bystander." 
- "Summarize in 3 bullets for supervisor handoff."

## Judge Checklist Mapping

- Beyond text UX: live camera + voice + interruption
- ADK/Gemini usage: real-time streaming with tool calls
- Robustness: short, deterministic tool path and concise fallback behavior
- Cloud native: deployed backend proof shown in video
- Demo quality: clear problem, live proof, architecture, value proposition
