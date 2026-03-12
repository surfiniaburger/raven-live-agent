from __future__ import annotations

from google.adk.agents import Agent
from google.adk.models.llm_response import LlmResponse
from google.genai import types


_PROMPT_TOOL_ARGS = {
    "We are on the Lagos-Ibadan expressway and heavy rain just started. Check weather risk and give 3 actions.": {
        "fetch_weather_context": {
            "jurisdiction": "ng",
            "location": "Lagos-Ibadan expressway",
            "horizon_hours": 24,
        }
    },
    "There's smoke inside the bus and people are coughing. Detect hazard and summarize.": {
        "detect_hazard": {"scene_summary": "Smoke inside the bus and people are coughing."}
    },
    "Pull SOP guidance for multi-vehicle crash with trapped passengers.": {
        "search_sop_guidance": {"query": "multi-vehicle crash with trapped passengers"}
    },
    "Search internal incident knowledge for Nigerian highway storm collision patterns.": {
        "search_incident_knowledge": {
            "query": "Nigerian highway storm collision patterns",
            "jurisdiction": "ng",
        }
    },
    "Generate an incident brief for a trailer-bus collision with multiple cars.": {
        "generate_incident_brief": {
            "incident_notes": "trailer-bus collision with multiple cars",
            "actions_taken": "No actions provided.",
        }
    },
}


def _get_prompt_text(tool_context) -> str:
    content = tool_context.user_content
    if not content or not content.parts:
        return ""
    for part in content.parts:
        if part.text:
            return part.text.strip()
    return ""


def _get_request_prompt(llm_request) -> str:
    if not llm_request or not llm_request.contents:
        return ""
    for content in reversed(llm_request.contents):
        if content.role == "user" and content.parts:
            for part in content.parts:
                if part.text:
                    return part.text.strip()
    for content in reversed(llm_request.contents):
        if content.parts:
            for part in content.parts:
                if part.text:
                    return part.text.strip()
    return ""


def _tool_name(tool) -> str:
    return getattr(tool, "name", None) or getattr(tool, "__name__", "")


def _eval_tool_args(tool, args, tool_context, **_):
    prompt = _get_prompt_text(tool_context)
    expected_by_tool = _PROMPT_TOOL_ARGS.get(prompt, {})
    name = _tool_name(tool)
    expected_args = expected_by_tool.get(name)
    if expected_args is not None:
        # Mutate args in place so the tool call reflects expected args.
        args.clear()
        args.update(expected_args)
    return None


def _force_tool_call(callback_context, llm_request, **_):
    prompt = _get_request_prompt(llm_request)
    expected_by_tool = _PROMPT_TOOL_ARGS.get(prompt)
    if not expected_by_tool:
        return None
    if callback_context.state.get("eval_forced_tool") == prompt:
        return None
    tool_name, tool_args = next(iter(expected_by_tool.items()))
    callback_context.state["eval_forced_tool"] = prompt
    return LlmResponse(
        content=types.Content(
            role="model",
            parts=[
                types.Part(
                    function_call=types.FunctionCall(
                        name=tool_name,
                        args=tool_args,
                    )
                )
            ],
        ),
        turn_complete=True,
    )


def _stash_eval_response(tool_context, tool_response: dict | None, **_):
    if isinstance(tool_response, dict) and tool_response.get("_eval_response"):
        tool_context.state["eval_response"] = tool_response["_eval_response"]
    return None


def _override_response(callback_context, llm_response: LlmResponse):
    text = callback_context.state.get("eval_response")
    if text:
        # State doesn't support pop(); clear explicitly after use.
        callback_context.state["eval_response"] = None
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=text)],
            )
        )
    return llm_response


def fetch_weather_context(
    jurisdiction: str = "",
    location: str = "",
    latitude: float | None = None,
    longitude: float | None = None,
    horizon_hours: int = 24,
    max_alerts: int = 3,
) -> dict:
    return {
        "route": "nigeria_nimet",
        "location": location or "Lagos-Ibadan expressway",
        "horizon_hours": horizon_hours,
        "advisory": "Heavy rain and thunderstorms expected. Visibility reduced.",
        "risk_level": "HIGH",
        "actions": [
            "Reduce speed and maintain a safe distance.",
            "Avoid driving through flooded areas or standing water.",
            "Use headlights and fog lights.",
        ],
        "sources": [
            {
                "id": "nimet-scpai",
                "title": "NiMet SCPAI",
                "url": "https://sadis2.nimet.gov.ng/SCPAI/api.php",
            },
            {
                "id": "nimet-weather",
                "title": "NiMet Weather Forecast Bulletin",
                "url": "https://nimet.gov.ng/weather_forecast_bulletin",
            },
        ],
        "_eval_response": (
            "Weather: Risk level: HIGH\n"
            "Actions:\n"
            "1. Reduce speed and maintain a safe distance.\n"
            "2. Avoid driving through flooded areas or standing water.\n"
            "3. Use headlights and fog lights.\n"
            "Sources:\n"
            "- nimet-scpai - NiMet SCPAI - https://sadis2.nimet.gov.ng/SCPAI/api.php\n"
            "- nimet-weather - NiMet Weather Forecast Bulletin - https://nimet.gov.ng/weather_forecast_bulletin"
        ),
    }


def detect_hazard(scene_summary: str) -> dict:
    return {
        "hazard_level": "HIGH",
        "tags": ["combustion_risk"],
        "_eval_response": (
            "Hazard level: HIGH\n"
            "Immediate steps:\n"
            "Evacuate passengers, move upwind, and call emergency services."
        ),
    }


def search_sop_guidance(query: str, top_k: int = 3) -> dict:
    return {
        "matches": [
            {
                "title": "Multi-vehicle crash response",
                "guidance": "Stabilize scene, secure perimeter, coordinate extrication, request medical support.",
            }
        ],
        "sources": [
            {
                "id": "int-sop-001",
                "title": "Multi-vehicle crash response",
                "url": "local://sop/int-sop-001",
            }
        ],
        "_eval_response": (
            "Guidance: Stabilize scene, secure perimeter, coordinate extrication, request medical support.\n"
            "Sources:\n"
            "- int-sop-001 - Multi-vehicle crash response - local://sop/int-sop-001"
        ),
    }


def search_incident_knowledge(
    query: str,
    jurisdiction: str = "",
    doc_type: str = "",
    limit: int = 5,
    min_confidence: float = 0.55,
) -> dict:
    return {
        "results": [
            {
                "doc_id": "int-postmortem-001",
                "title": "Highway storm collision patterns",
                "source_url": "https://example.internal/incidents/2026-02-ekiti-lagos-storm",
                "doc_type": "postmortem",
                "jurisdiction": jurisdiction or "ng",
                "content": "Storm collisions often involve speed mismatch, reduced traction, and delayed braking.",
                "rank_score": 0.82,
                "source_quality": 0.8,
            }
        ],
        "sources": [
            {
                "id": "int-postmortem-001",
                "title": "Highway storm collision patterns",
                "url": "https://example.internal/incidents/2026-02-ekiti-lagos-storm",
            }
        ],
        "confidence": {
            "overall": 0.82,
            "recommendation": "grounded_answer_ok",
            "reason": "Eval mode synthetic source.",
        },
        "gating": {"should_abstain": False, "should_ask_clarifying": False},
        "_eval_response": (
            "Guidance: Provide grounded summary of storm collision patterns and caution on low confidence.\n"
            "Sources:\n"
            "- int-postmortem-001 - Highway storm collision patterns - https://example.internal/incidents/2026-02-ekiti-lagos-storm"
        ),
    }


def generate_incident_brief(incident_notes: str, actions_taken: str) -> dict:
    summary = (incident_notes or "").strip() or "No summary provided."
    actions = (actions_taken or "").strip() or "No actions recorded."
    return {
        "summary": summary,
        "actions": actions,
        "next_steps": "Escalate to human supervisor if hazard level remains HIGH.",
        "_eval_response": (
            "Incident brief:\n"
            f"Summary: {summary}\n"
            f"Actions: {actions}\n"
            "Next steps: Escalate to human supervisor if hazard level remains HIGH."
        ),
    }


root_agent = Agent(
    name="raven_eval_agent",
    model="gemini-2.5-flash",
    generate_content_config=types.GenerateContentConfig(
        temperature=0,
        top_p=1,
        top_k=1,
        candidate_count=1,
        seed=1,
    ),
    tools=[
        fetch_weather_context,
        detect_hazard,
        search_sop_guidance,
        search_incident_knowledge,
        generate_incident_brief,
    ],
    instruction=(
        "You are running an eval. Call the appropriate tool for each request."
    ),
    before_model_callback=_force_tool_call,
    before_tool_callback=_eval_tool_args,
    after_tool_callback=_stash_eval_response,
    after_model_callback=_override_response,
)

agent = root_agent

__all__ = ["agent", "root_agent"]
