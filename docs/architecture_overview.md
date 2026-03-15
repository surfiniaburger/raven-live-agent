# RAVEN Architecture Overview

The following diagram illustrates the flow of data between the User Interface, the Backend (FastAPI), the Gemini Live API, and the Fallback engine (ElevenLabs).

```mermaid
graph TD
    subgraph Frontend [React Application]
        UI[User Interface]
        AS[AudioStreamer - Playback]
        AR[AudioRecorder - Capture]
        VAD[WebRTC VAD - MicVAD]
    end

    subgraph Backend [FastAPI / Python]
        MAIN[main.py - WebSocket Manager]
        AGENT[Live Incident Agent]
        TOOLS[Grounding & Risk Tools]
        FALLBACK[ElevenLabs Fallback Engine]
    end

    subgraph External [External APIs]
        GEMINI[Gemini Flash Live API]
        11LABS[ElevenLabs STT/TTS]
        NIMET[NiMet Weather API - NG]
        WEATHER[Weather.gov API - US]
        VSEARCH[Vertex AI Vector Search 2.0]
    end

    %% Audio Flows
    AR -->|PCM16| MAIN
    MAIN -->|Bimodal Stream| GEMINI
    GEMINI -->|Audio Chunks| AS

    %% Control Flows
    VAD -->|onSpeechStart| UI
    VAD -->|onSpeechEnd| MAIN
    UI -->|Barge-in/Interrupt| MAIN
    MAIN -->|Control Frame| GEMINI

    %% Tool/Grounding Flows
    GEMINI -->|Tool Call| MAIN
    MAIN -->|Execute| TOOLS
    TOOLS -->|Request| NIMET
    TOOLS -->|Request| WEATHER
    TOOLS -->|SOP Search| MAIN
    TOOLS -->|Hybrid Search| VSEARCH
    
    %% Fallback Logic
    MAIN -.->|On Error/1008| FALLBACK
    FALLBACK <--->|WebSocket| 11LABS
```

### Component Details
- **WebRTC VAD (`@ricky0123/vad-web`)**: Runs client-side for low-latency speech detection. Triggers barge-ins locally and sends "speech end" signals to finalize transactions.
- **FastAPI WebSocket**: Acts as the central hub. Routes audio to/from Gemini and handles tool execution.
- **Support Tools**:
    - **Grounding Tools**: Bridges the agent to real-world weather data.
    - **Risk Tools**: Classifies scene data into hazard levels.
    - **Vector Search 2.0**: Specialized hybrid search (Semantic + Lexical) for historical incident knowledge.
    - **SOP Catalog**: local `.json` database of safety procedures.
- **ElevenLabs Fallback**: Activated automatically if the primary Gemini stream encounters a policy violation (e.g., restricted content) or connection error.
