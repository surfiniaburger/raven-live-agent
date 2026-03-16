# RAVEN: From Highway Trauma to Real-Time AI Response

### Turning Live Multi-Modal Perception into Actionable Emergency Navigation

---

**Disclaimer:** *This piece of content was created for the purposes of entering the Gemini Live Agent Challenge hackathon. #GeminiLiveAgentChallenge*

---

## 1. The "Why": A Storm on the Lagos-Ibadan Expressway

In September 2025, a celebratory trip to my brother’s wedding introduction in Ondo State ended in a violent storm on the highway back to Lagos. Visibility vanished. Seconds later, a trailer, a nine-seater bus, and several cars collided in a cascading wreck. 

Being in the center of that chaos revealed a fatal gap in our technology: in high-risk moments, we don't need a chatbot. We need a partner that sees what we see, hears the panic in our voice, and provides grounded, definitive guidance when our own judgment is paralyzed by stress. 

**RAVEN (Real-time Agent for Visual Emergency Navigation)** was built to close that gap.

## 2. Beyond the Chatbox: The Multi-Modal Shift

The defining characteristic of an emergency is **Decision Lag**. Every second spent typing a prompt or waiting for a slow text-to-speech engine is a second lost to chaos.

RAVEN shifts the paradigm from "Asynchronous Chat" to "Synchronous Perception." By utilizing the **Gemini 1.5 Flash (Native Audio)** model, RAVEN maintains a bidirectional stream of high-fidelity audio and visual telemetry. It doesn't just process text; it identifies the color of smoke, the sound of sizzling battery acid, and the atmospheric context of a storm—all in real-time.

## 3. Under the Hood: The Agent Development Kit (ADK)

Building a live, multi-modal agent is technically demanding. Managing WebSocket message contracts, tool-calling loops, and session persistence from scratch is a massive undertaking. 

We leveraged the **Google Agent Development Kit (ADK)** to handle this "plumbing." ADK allowed us to focus on the high-level agentic logic by providing:
- **Streaming Session Management**: Handling the state of a live conversation over a multi-minute session.
- **Bidi-Streaming Loops**: Seamlessly routing PCM audio buffers between the frontend and the Gemini Live API.
- **Tool-Calling Orchestration**: Enabling the agent to "pause" and fetch weather advisories from NiMet or safety protocols from our library without breaking the conversational flow.

## 4. The "Fast-Interrupt": Solving for Human Reality

One of our biggest challenges was **interruption latency**. If a user yells "STOP!" because a fire has broken out, the AI must cease speaking instantly. 

We implemented a custom **"Fast-Interrupt" path** using client-side **WebRTC VAD (`@ricky0123/vad-web`)**. The frontend detects speech onset locally, immediately flushes the audio playback buffer, and sends a control signal to the backend. This ensures the human is always the lead in the interaction, a critical safety requirement for operational environments.

## 5. Grounding in Truth: Vertex AI Vector Search 2.0

In emergency navigation, hallucinations are dangerous. To ensure RAVEN's advice is citeable and trustworthy, we integrated **Vertex AI Vector Search 2.0**. 

When a user asks for an SOP (Standard Operating Procedure), RAVEN performs a **Hybrid Semantic + Lexical Search** across our verified knowledge base. By using Reciprocal Rank Fusion (RRF), we combine the contextual power of embeddings with the exactness of keyword matching (e.g., retrieving the specific "Chemical Spill" protocol when "oily liquid" is mentioned). 

## 6. Closing: Built for the Real World

RAVEN isn't just a prototype; it's a cloud-native ecosystem deployed on **Google Cloud Run** with a fully automated CI/CD pipeline. 

Building with Gemini and the ADK showed us that the future of AI isn't just smarter models—it's more responsive ones. By turning live perception into actionable response, we can move from merely chatting with AI to relying on it when it matters most.

---

**Explore the project:**
- [GitHub Repository](https://github.com/surfiniaburger/raven-live-agent)
- [Devpost Submission](https://devpost.com/software/raven-emergency-navigation)

*#GoogleCloud #Gemini #ADK #AI #EmergencyResponse*
