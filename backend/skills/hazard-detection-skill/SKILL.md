---
name: hazard-detection-skill
description: Detect immediate hazards from user-described scene and return operational steps.
---

Use this skill when the user asks about hazards, safety risks, smoke/fire, chemicals, collisions, or unsafe environments.

Steps:
1. Call `detect_hazard` with a concise `scene_summary` built from the user description.
   - Remove instruction phrases like "detect hazard" or "scan".
   - Use the user's own phrasing where possible.

Response format:
- Hazard: "Hazard level:", "Immediate steps:"

Rules:
- Keep steps short and action-first.
- If immediate danger is present, prioritize evacuation and emergency contact steps.
