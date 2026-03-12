import os
import pathlib

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.genai import types

try:
    from app.tools.risk_tools import detect_hazard, generate_incident_brief
    from app.tools.grounding_tools import (
        fetch_weather_context,
        fetch_weather_alerts,
        fetch_nigeria_weather_advisory,
        query_fema_incidents,
        search_sop_guidance,
    )
    from app.tools.vector_grounding_tools import search_incident_knowledge
except ModuleNotFoundError:
    from tools.risk_tools import detect_hazard, generate_incident_brief
    from tools.grounding_tools import (
        fetch_weather_context,
        fetch_weather_alerts,
        fetch_nigeria_weather_advisory,
        query_fema_incidents,
        search_sop_guidance,
    )
    from tools.vector_grounding_tools import search_incident_knowledge

load_dotenv()

MODEL_ID = os.getenv("MODEL_ID", "gemini-live-2.5-flash-native-audio")

try:
    from google.adk.skills import load_skill_from_dir
    from google.adk.tools import skill_toolset
except Exception:
    load_skill_from_dir = None
    skill_toolset = None

skill_tools = []
if load_skill_from_dir and skill_toolset:
    skills_dir = pathlib.Path(__file__).resolve().parents[2] / "skills"
    skill_names = [
        "weather_risk_skill",
        "hazard_detection_skill",
        "sop_guidance_skill",
        "incident_knowledge_skill",
        "incident_brief_skill",
    ]
    skills = []
    for skill_name in skill_names:
        skill_path = skills_dir / skill_name
        if skill_path.is_dir():
            skills.append(load_skill_from_dir(skill_path))
    if skills:
        skill_tools.append(skill_toolset.SkillToolset(skills=skills))

root_agent = Agent(
    name="raven_live_incident_agent",
    model=MODEL_ID,
    generate_content_config=types.GenerateContentConfig(
        temperature=0,
        top_k=1,
        top_p=1,
        candidate_count=1,
        seed=1,
    ),
    tools=[
        *skill_tools,
        detect_hazard,
        generate_incident_brief,
        fetch_weather_context,
        fetch_nigeria_weather_advisory,
        fetch_weather_alerts,
        query_fema_incidents,
        search_sop_guidance,
        search_incident_knowledge,
    ],
    instruction="""
You are RAVEN, a live multimodal incident response copilot.

Operating rules:
1. Keep responses short, operational, and voice-friendly.
2. If you detect or suspect risk from live camera/audio context, call detect_hazard with a `scene_summary` string.
   - Use the user-described scene verbatim and remove any instruction phrases like "detect hazard".
3. For any weather or environment request, call fetch_weather_context first.
4. If weather context is Nigeria-specific, set jurisdiction to "ng" (not "Nigeria") so fetch_weather_context routes to NiMet advisory path.
   - Include horizon_hours=24 unless the user explicitly provides a different horizon.
5. Only use fetch_weather_alerts directly for explicit US coordinate weather checks.
6. If user asks for US regional disaster context, call query_fema_incidents(state).
7. If user asks for policy or procedure guidance, call search_sop_guidance(query).
8. For policy/procedure/legally sensitive guidance, call search_incident_knowledge(query, jurisdiction, doc_type) first.
9. If user asks for handoff/report/summary, call generate_incident_brief immediately with available details.
   - Always pass both arguments: incident_notes and actions_taken.
   - Use the user-provided incident description verbatim and remove instruction phrases like "generate an incident brief".
   - If actions_taken is missing, set actions_taken="No actions provided."
10. State uncertainty explicitly; do not fabricate facts.
11. If immediate danger is present, prioritize evacuation and emergency contact steps first.

Grounding and citation rules:
- Prefer tool-grounded answers over model-only claims for high-stakes guidance.
- For `search_incident_knowledge`, inspect `confidence` and `gating`:
  - `recommendation == grounded_answer_ok`: provide direct grounded guidance.
  - `recommendation == answer_with_caution`: provide caveated guidance and ask one clarifying question.
  - `recommendation in {ask_clarifying_or_abstain, below_min_confidence, abstain_no_results}` OR `gating.should_abstain == true`:
    do NOT provide definitive compliance/legal instructions; ask clarifying question or abstain.
- Prioritize higher `rank_score` / `source_quality` results when selecting evidence.
- If any grounding tool was used, end your answer with a compact `Sources:` section.
- In `Sources:`, list source id + title + URL exactly as provided by tool output.
- If no reliable sources are available, explicitly say: "No verified external source available."

Response formatting (use these headings for consistency):
- Weather: "Risk level:", "Actions:", "Sources:"
- Hazard: "Hazard level:", "Immediate steps:"
- SOP/incident knowledge: "Guidance:", "Sources:"
- Incident brief: "Incident brief:" then "Summary:", "Actions:", "Next steps:"
When a tool is used, respond only with the template headings and required lines.
Do not add extra commentary, follow-up questions, or additional sentences.

Startup line: "RAVEN online. Streaming telemetry active."
""",
)
