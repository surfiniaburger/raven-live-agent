"""Core risk tools for the RAVEN live incident agent."""

from datetime import datetime, timezone


def detect_hazard(scene_summary: str) -> dict:
    """Return a normalized hazard assessment from the scene summary."""
    summary = (scene_summary or "").lower()
    level = "LOW"
    tags = []

    if any(token in summary for token in ["smoke", "fire", "sparks", "gas", "leak"]):
        level = "HIGH"
        tags.append("combustion_risk")
    elif any(token in summary for token in ["spill", "broken glass", "crowd", "panic"]):
        level = "MEDIUM"
        tags.append("site_safety")

    return {
        "hazard_level": level,
        "tags": tags,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def generate_incident_brief(incident_notes: str, actions_taken: str) -> dict:
    """Create a compact incident brief for handoff and auditing."""
    return {
        "summary": incident_notes.strip() if incident_notes else "No summary provided.",
        "actions": actions_taken.strip() if actions_taken else "No actions recorded.",
        "next_steps": "Escalate to human supervisor if hazard level remains HIGH.",
    }
