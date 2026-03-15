# RAVEN Demo Script: "The Highway Sentinel"

This script is designed for a single-session demonstration that moves from initial contact to a high-stress crisis management moment.

## Preparation
1. Ensure `ELEVENLABS_API_KEY` is set for fallback demo.
2. Have a small, safe flame source (like a lighter or burning paper) if showing visual hazard detection via description.

---

## Act 1: The Observer (Tool: Grounding)
**Narrative:** You are a first responder arriving at a scene in Nigeria during the 2026 storm season.

**User:** 
> "RAVEN, I've just pulled up at the Lagos-Ibadan expressway interchange. The wind is extreme and visibility is dropping to almost zero. Can you check the NiMet weather advisory for this exact route and let me know if there's a flood risk?"

**Expected System Behavior:**
- **Tool Call:** `fetch_weather_context(jurisdiction="Nigeria", location="Lagos-Ibadan expressway")`.
- **Logic:** The backend routes to `fetch_nigeria_weather_advisory`, which hits the NiMet API.
- **Response:** Agent reports risk level (e.g., HIGH) and lists 3 road safety actions.

---

## Act 2: The Assessment (Tool: Risk Analysis)
**Narrative:** The situation escalates. You notice sensory details that imply a worsening fire.

**User:** 
> "Copy that. I'm approaching a trapped bus now. I see thick white smoke coming from the engine compartment, and I'm smelling something like ozone or burning plastic. There are people still on board. Give me a hazard assessment immediately."

**Expected System Behavior:**
- **Tool Call:** `detect_hazard(scene_summary="thick white smoke, ozone, burning plastic, trapped passengers")`.
- **Logic:** `risk_tools.py` scans for keywords. "Smoke" triggers `HAZARD_LEVEL: HIGH` and tagging `combustion_risk`.
- **Response:** Agent warns of active fire risk and prioritizes evacuation.

---

## Act 3: The Library (Tool: SOP Retrieval)
**Narrative:** You need the exact protocol.

**User:** 
> "The smoke is turning black and there's a liquid spill spreading onto the tarmac. It looks oily. Pull up the standard operating procedure for chemical spills and fire evacuation. I need to know how to handle the crowd that's forming."

**Expected System Behavior:**
- **Tool Call:** `search_sop_guidance(query="liquid spill oily fire evacuation crowd")`.
- **Logic:** Searches `sop_catalog.json`. Matches `evac-001` (Evacuation), `spill-003` (Chemical), and `crowd-004` (Crowd Safety).
- **Response:** Merges guidance into a step-by-step priority list.

---

## Act 4: The Archive (Tool: Incident Knowledge / Vector Search)
**Narrative:** You need to check if this "sizzling battery" is a known pattern from previous highway storm incidents.

**User:** 
> "Wait! Stop! I just identified the spill—it's coming from an industrial battery pack that fell off a trailer. The fluid is sizzling on the ground! Do we have any record of this happening in previous Nigerian storm collisions? Search our incident knowledge base for patterns."

**Expected System Behavior:**
- **VAD Action:** `MicVAD` detects speech start while `assistantSpeaking.current` is true.
- **AudioStreamer:** Instantly cancels the current audio buffer (Barge-in).
- **Tool Call:** `search_incident_knowledge(query="industrial battery sizzling fluid Nigerian storm collision")`.
- **Logic:** Calls `vector_grounding_tools.py` which triggers a **Hybrid Semantic + Lexical Search** via Vertex AI Vector Search 2.0.
- **Response:** Reports historical patterns (e.g., thermal runaway in high-humidity storms) and specific cautions on hazardous runoff.

## Act 5: The Pivot (Feature: Barge-in / Interrupt)
**Narrative:** *Trigger this while the agent is midway through a long SOP list.*

**User (Barge-in):** 
> "Wait! Stop! I just identified the spill—it's coming from an industrial battery pack that fell off a trailer. The fluid is sizzling on the ground!"

**Expected System Behavior:**
- **VAD Action:** `MicVAD` detects speech start while `assistantSpeaking.current` is true.
- **AudioStreamer:** Instantly cancels the current audio buffer.
- **Logic:** Backend receives the interrupt. Gemini processes the new context (electrical threat).
- **Tool Call:** `search_sop_guidance(query="battery pack sizzling ground")`.
- **Response:** Switches to `elec-002` (Electrical Hazard) protocol: "Do not touch exposed wires... keep 3-meter perimeter."

---

## Act 6: The Handoff (Final Report)
**Narrative:** Scene stabilized.

**User:** 
> "Area secured. Power is isolated. Paramedics are taking over. Compile our notes into an incident brief for the handoff."

**Expected System Behavior:**
- **Tool Call:** `generate_incident_brief`.
- **Response:** Summarizes the weather context, fire/smoke hazard, battery threat, and actions taken (Evacuated, SOPs followed).
