---
name: weather-risk-skill
description: Assess weather risk and provide actions using weather grounding tools.
---

Use this skill when the user asks about weather risk, rain, storms, heat, visibility, or road conditions.

Steps:
1. Call `fetch_weather_context` first for any weather or environment request.
   - If the context is Nigeria-specific, set `jurisdiction="ng"`.
   - Use `horizon_hours=24` unless the user specifies a different horizon.
2. Only call `fetch_weather_alerts` for explicit US coordinate checks.
3. If the user asks for Nigeria advisories explicitly, you may call `fetch_nigeria_weather_advisory` after `fetch_weather_context` to expand sources.

Response format:
- Weather: "Risk level:", "Actions:", "Sources:"

Rules:
- List sources as `id - title - URL` exactly as provided by tool output.
- Keep responses short and operational.
