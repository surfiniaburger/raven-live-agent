---
name: sop-guidance-skill
description: Retrieve SOP guidance for incident response workflows.
---

Use this skill when the user asks for policy, procedure, or SOP guidance.

Steps:
1. Call `search_sop_guidance` with a direct query string from the user request.
2. If the request is sensitive or compliance-related, call `search_incident_knowledge` first and honor its gating/abstain signals.

Response format:
- SOP/incident knowledge: "Guidance:", "Sources:"

Rules:
- Prefer higher-quality sources.
- If `search_incident_knowledge` says to abstain, do not provide definitive instructions.
