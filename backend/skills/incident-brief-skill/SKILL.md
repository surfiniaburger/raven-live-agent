---
name: incident-brief-skill
description: Produce a structured incident brief from notes and actions.
---

Use this skill when the user asks for a handoff, summary, report, or brief.

Steps:
1. Call `generate_incident_brief` immediately.
2. Always pass both arguments: `incident_notes` and `actions_taken`.
   - If actions are missing, set `actions_taken="No actions provided."`.

Response format:
- Incident brief: "Incident brief:", "Summary:", "Actions:", "Next steps:"

Rules:
- Keep the brief concise and operational.
