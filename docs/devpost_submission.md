# RAVEN: Real-time Agent for Visual Emergency Navigation

## Inspiration

September 2025 started as a celebratory trip—my family was traveling to Ondo State for my brother’s wedding introduction. On our way back to Lagos, a massive storm broke. Within minutes, the highway turned into a scene of industrial tragedy: a trailer, a nine-seater bus, and several small cars had collided in a cascading sequence of steel and glass. The bus was sandwiched, lives were being lost, and the air was thick with panic.

Being in the middle of that chaos made one thing brutally clear: in the heat of a disaster, humans don't need another chatbot; they need a partner. Fragmented info, delayed judgment, and the sheer paralytic stress of the moment are "secondary casualties." RAVEN was built from that pain—to turn live perception into actionable response.

## What it does

RAVEN is a **multimodal incident response copilot** designed for high-risk environments. It doesn't wait for you to type; it sees what you see and hears what you hear in real-time.

- **Live Perception**: Streams camera and microphone telemetry over a bidirectional WebSocket pipeline using the Gemini Live API.
- **Hazard Detection**: Automatically identifies risks like combustion indicators (smoke/smell), structural instability, and electrical threats.
- **Grounded SOP Guidance**: Uses Vertex AI Vector Search 2.0 to retrieve verified Standard Operating Procedures (SOPs) and historical incident knowledge.
- **Seamless Interruption (Barge-in)**: Allows users to interrupt the AI mid-sentence for urgent updates, ensuring the agent is always following the human's immediate reality.
- **Incident Briefing**: Generates deterministic, handoff-ready reports for emergency responders and insurance triage.

## How we built it

RAVEN is a cloud-native agentic system built on the **Google Cloud Platform**:

- **Agentic Core**: Orchestrated using the **Google Agent Development Kit (ADK)** to manage complex tool-calling loops and session persistence.
- **AI Model**: Leverages the **Gemini 1.5 Flash (Native Audio)** model for low-latency, multimodal reasoning.
- **Vector Search 2.0**: Implemented hybrid (Semantic + Lexical) search for grounding safety protocols, ensuring guidance is cited and trustworthy.
- **Frontend**: A React-based interface utilizing **WebRTC VAD (`@ricky0123/vad-web`)** for client-side voice activity detection.
- **Backend**: A FastAPI server deployed to **Google Cloud Run** with an automated **Cloud Build** CI/CD pipeline.
- **Fallback Resilience**: Integrated **ElevenLabs STT/TTS** as an automated fallback engine to ensure conversational continuity even if the primary stream hits safety policy constraints.

## Challenges we ran into

1. **Managing Latency in Bidi-Streaming**: Real-time audio processing required a "Fast-Interrupt" path where the frontend stops talking the moment a user's voice is detected, syncing that state back to the model only milliseconds later.
2. **Hybrid Search Accuracy**: Balancing semantic similarity with exact keyword matching in the SOP catalog was tricky. We solved this by implementing **Reciprocal Rank Fusion (RRF)** in Vertex AI Vector Search 2.0.
3. **Conversational Fluidity vs. Grounding**: Ensuring the agent sounds "human" while adhering to strict, documented safety protocols required careful prompt engineering and ADK session management.

## Accomplishments that we're proud of

- **"Local-First" Interruption**: We achieved a zero-perceived-latency barge-in mechanism.
- **Verification of Grounding**: Built a confidence-aware gating system that prevents the AI from hallucinating safety advice when SOP data is ambiguous.
- **End-to-End GCP Automation**: From infrastructure-as-code deployment scripts to real-time Vertex AI grounding, RAVEN is a production-ready ecosystem.

## What we learned

- **ADK is Game-Changing**: It abstracted away the "plumbing" of streaming and tool-calling, allowing us to focus on the high-level agentic logic.
- **Multimodal Context is King**: Seeing and hearing simultaneously allows the model to catch nuances (like the color of smoke or the specific sound of a sizzle) that a text-only prompt would miss.
- **Trust requires Grounding**: In emergency navigation, a 99% accurate answer isn't enough; the ability to cite a specific SOP file is what builds user trust.

## What's next for RAVEN

- **Fleet Safety Integration**: Deploying RAVEN as a built-in copilot for long-haul logistics fleets in the West African corridor.
- **Insurance FNOL Automation**: Using the recorded multimodal session to automate "First Notice of Loss" for insurance claims.
- **Multi-Agent Coordination**: Enabling RAVEN to "talk" to other RAVEN instances on-site, coordinating a multi-person response across a large disaster area.
