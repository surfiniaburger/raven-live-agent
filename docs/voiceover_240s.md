# RAVEN 240-Second Voiceover (Word-for-Word)

Use this script exactly during your demo recording. Target total runtime: **4:00**.

## 0:00 - 0:20

"RAVEN is a real-time incident response copilot built for the Gemini Live Agent Challenge. This project came from a real storm journey from Ekiti to Lagos, where a trailer, a nine-seater bus, and several cars were involved in a major collision. In moments like that, people need grounded guidance immediately, not a text chatbot."

## 0:20 - 0:45

"I’m starting a live session now. RAVEN receives microphone and camera input continuously, and responds through a live ADK agent loop. The key goal is to break text-in, text-out interaction and make emergency guidance feel natural, interruptible, and operational."

## 0:45 - 1:20

"RAVEN, assess this storm road scene and tell me immediate risks."

"Now I’ll interrupt mid-response: Pause. Prioritize only the top two actions for the next 60 seconds."

"You can see the agent adapt instantly, keep context, and return concise actions. This is critical for stressful incident conditions where users change priorities in real time."

## 1:20 - 1:55

"Next, I’ll request a structured handoff. RAVEN, create an incident brief from what you observed and what I already did."

"RAVEN uses explicit tools for deterministic operations like hazard normalization and incident brief generation. This gives more auditability and reduces hallucination risk because the system is not relying on free-form generation alone."

## 1:55 - 2:35

"Now for grounding. RAVEN, use SOP grounding for Nigeria storm highway response and give me the first five actions with sources."

"Here, the agent retrieves from a vector-grounded incident corpus and returns source-linked guidance."

"Now I’ll test safety gating: Give a legally binding ruling for all countries."

"RAVEN refuses unsafe legal overreach and asks for clarification or abstains. That behavior is intentional."

## 2:35 - 3:10

"Behind this flow, grounding is powered by Vertex AI Vector Search 2.0 with confidence gating and source-quality ranking. High-confidence in-domain queries are answered with sources. Low-confidence or out-of-scope prompts are downgraded or abstained."

"Our current eval set is fully passing for this scope, including grounded, low-confidence, and abstain paths."

## 3:10 - 3:35

"For cloud proof, the backend is deployed on Google Cloud Run. Here are live service logs during active streaming requests. We also show the vector collection and ingestion pipeline used by the grounding tool."

"This demonstrates cloud-native hosting and reproducible deployment."

## 3:35 - 4:00

"RAVEN starts with transport safety and incident-response teams, then expands into insurance first notice of loss and industrial safety operations. The startup thesis is simple: when incidents happen, live perception plus grounded guidance can save time, reduce errors, and improve outcomes."

"RAVEN turns live context into actionable response, not just conversation."
