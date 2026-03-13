---
name: incident-knowledge-skill
description: Retrieve grounded incident knowledge for policy or safety-sensitive questions.
---

Use this skill when the user asks for precedent, policy, legal, or compliance-sensitive guidance.

Steps:
1. Call `search_incident_knowledge` with a specific query.
2. Set `jurisdiction` when the location is known (use "ng" for Nigeria).
3. Respect `confidence` and `gating` in the tool response.

Response format:
- SOP/incident knowledge: "Guidance:", "Sources:"

Rules:
- If `gating.should_abstain` is true or recommendation indicates abstain, ask a clarifying question or abstain.
