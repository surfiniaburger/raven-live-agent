"""Grounding tools for external context and internal SOP retrieval."""

from __future__ import annotations

import json
import time
import urllib.parse
from pathlib import Path
from typing import Any

import httpx

_TIMEOUT_SECONDS = 8.0
_RETRY_ATTEMPTS = 3
_BACKOFF_SECONDS = 0.6
_SOP_PATH = Path(__file__).resolve().parent.parent / "data" / "sop_catalog.json"
_NIMET_SCPAI_URL = "https://sadis2.nimet.gov.ng/SCPAI/api.php"


def _http_get_json(
    client: httpx.Client,
    url: str,
    attempts: int = _RETRY_ATTEMPTS,
    backoff_seconds: float = _BACKOFF_SECONDS,
) -> tuple[dict[str, Any] | None, str | None]:
    """GET JSON with simple retry/backoff for transient failures."""
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.json(), None
        except Exception as exc:  # noqa: BLE001
            last_error = f"attempt_{attempt}: {exc}"
            if attempt < attempts:
                time.sleep(backoff_seconds * attempt)
    return None, last_error


def fetch_weather_alerts(latitude: float, longitude: float, max_alerts: int = 3) -> dict[str, Any]:
    """Fetch active weather alerts around a coordinate using weather.gov APIs."""
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        return {"alerts": [], "sources": [], "error": "Invalid coordinates."}

    headers = {"User-Agent": "raven-live-agent/0.1 (ops@example.com)"}
    client = httpx.Client(timeout=_TIMEOUT_SECONDS, headers=headers)
    try:
        points_url = f"https://api.weather.gov/points/{latitude},{longitude}"
        points, points_error = _http_get_json(client, points_url)
        if points is None:
            return {
                "alerts": [],
                "sources": [{"id": "weather.gov", "title": "US National Weather Service", "url": points_url}],
                "error": f"weather_points_failed: {points_error}",
            }

        county = (
            points.get("properties", {})
            .get("county", "")
            .split("/")[-1]
        )
        if not county:
            return {"alerts": [], "sources": [], "note": "No county found for coordinate."}

        alerts_url = f"https://api.weather.gov/alerts/active?zone={county}"
        alerts_payload, alerts_error = _http_get_json(client, alerts_url)
        if alerts_payload is None:
            return {
                "alerts": [],
                "sources": [{"id": "weather.gov", "title": "US National Weather Service Alerts", "url": alerts_url}],
                "error": f"weather_alerts_failed: {alerts_error}",
            }

        features = alerts_payload.get("features", [])[: max(1, min(max_alerts, 10))]
        alerts = []
        for item in features:
            props = item.get("properties", {})
            alerts.append(
                {
                    "event": props.get("event"),
                    "severity": props.get("severity"),
                    "headline": props.get("headline"),
                    "effective": props.get("effective"),
                    "expires": props.get("expires"),
                }
            )

        return {
            "alerts": alerts,
            "sources": [
                {"id": "weather.gov", "title": "US National Weather Service Alerts", "url": alerts_url}
            ],
            "meta": {"retry_attempts": _RETRY_ATTEMPTS},
        }
    except Exception as exc:  # noqa: BLE001
        return {"alerts": [], "sources": [], "error": f"weather_lookup_failed: {exc}"}
    finally:
        client.close()


def _infer_risk_level(text: str) -> str:
    raw = (text or "").lower()
    if any(t in raw for t in ["severe", "extreme", "flood", "danger", "thunderstorm", "heavy rain"]):
        return "HIGH"
    if any(t in raw for t in ["showers", "moderate", "caution", "poor visibility"]):
        return "MEDIUM"
    if raw.strip():
        return "LOW"
    return "UNKNOWN"


def _extract_actions(text: str, max_actions: int = 3) -> list[str]:
    if not text:
        return []
    actions = []
    for chunk in text.replace("\r", " ").split("."):
        sent = chunk.strip()
        if len(sent) < 28:
            continue
        if any(k in sent.lower() for k in ["should", "avoid", "ensure", "reduce", "monitor", "check", "keep"]):
            actions.append(sent)
        if len(actions) >= max_actions:
            break
    return actions


def fetch_nigeria_weather_advisory(location: str, horizon_hours: int = 24) -> dict[str, Any]:
    """Fetch Nigeria weather advisory context from NiMet SCPAI endpoint.

    Args:
        location: City/state/route context (e.g. "Lagos-Ibadan expressway").
        horizon_hours: Forecast horizon for query context (default 24).
    """
    loc = (location or "").strip()
    if len(loc) < 2:
        return {"advisory": "", "risk_level": "UNKNOWN", "actions": [], "sources": [], "error": "Location is required."}

    hours = max(6, min(horizon_hours, 72))
    prompt = (
        f"Provide weather warning guidance for {loc}, Nigeria for the next {hours} hours. "
        "Include heavy rain or thunderstorm risk, visibility caution, and 3 short road safety actions."
    )
    url = f"{_NIMET_SCPAI_URL}?question={urllib.parse.quote(prompt)}"

    client = httpx.Client(timeout=_TIMEOUT_SECONDS)
    try:
        payload, req_error = _http_get_json(client, url)
        if payload is None:
            return {
                "advisory": "",
                "risk_level": "UNKNOWN",
                "actions": [],
                "sources": [
                    {"id": "nimet-scpai", "title": "NiMet SCPAI", "url": url},
                    {"id": "nimet-weather", "title": "NiMet Weather Forecast Bulletin", "url": "https://nimet.gov.ng/weather_forecast_bulletin"},
                ],
                "error": f"nimet_query_failed: {req_error}",
            }

        answer = (payload.get("answer") or payload.get("response") or "").strip()
        risk_level = _infer_risk_level(answer)
        actions = _extract_actions(answer)

        return {
            "location": loc,
            "horizon_hours": hours,
            "advisory": answer,
            "risk_level": risk_level,
            "actions": actions,
            "sources": [
                {"id": "nimet-scpai", "title": "NiMet SCPAI", "url": url},
                {"id": "nimet-weather", "title": "NiMet Weather Forecast Bulletin", "url": "https://nimet.gov.ng/weather_forecast_bulletin"},
            ],
            "meta": {"retry_attempts": _RETRY_ATTEMPTS},
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "advisory": "",
            "risk_level": "UNKNOWN",
            "actions": [],
            "sources": [],
            "error": f"nimet_lookup_failed: {exc}",
        }
    finally:
        client.close()


def fetch_weather_context(
    jurisdiction: str = "",
    location: str = "",
    latitude: float | None = None,
    longitude: float | None = None,
    horizon_hours: int = 24,
    max_alerts: int = 3,
) -> dict[str, Any]:
    """Route weather lookup by jurisdiction with a safe default.

    Priority:
    1) Nigeria jurisdiction/location -> NiMet advisory path.
    2) Valid coordinates -> weather.gov alert path.
    3) Otherwise return clarifying guidance.
    """
    j = (jurisdiction or "").strip().lower()
    loc = (location or "").strip()
    loc_l = loc.lower()
    nigeria_hint = any(token in loc_l for token in ["nigeria", "lagos", "abuja", "ibadan", "port harcourt", "kano"])

    if j in {"ng", "nga", "nigeria"} or nigeria_hint:
        payload = fetch_nigeria_weather_advisory(location=loc or "Nigeria", horizon_hours=horizon_hours)
        payload["route"] = "nigeria_nimet"
        return payload

    has_coords = latitude is not None and longitude is not None
    if has_coords:
        payload = fetch_weather_alerts(
            latitude=float(latitude),
            longitude=float(longitude),
            max_alerts=max_alerts,
        )
        payload["route"] = "us_weather_gov"
        return payload

    return {
        "route": "clarify_required",
        "advisory": "",
        "risk_level": "UNKNOWN",
        "actions": [],
        "sources": [],
        "note": "Provide jurisdiction/location for Nigeria advisory or coordinates for US weather alerts.",
    }


def query_fema_incidents(state: str, limit: int = 5) -> dict[str, Any]:
    """Fetch recent FEMA disaster declarations for a US state code."""
    safe_state = (state or "").strip().upper()[:2]
    safe_limit = max(1, min(limit, 20))
    if len(safe_state) != 2:
        return {"incidents": [], "sources": [], "error": "State must be a 2-letter US code."}

    base_url = "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries"
    url = (
        f"{base_url}?$filter=state eq '{safe_state}'"
        f"&$orderby=declarationDate desc&$top={safe_limit}"
    )

    client = httpx.Client(timeout=_TIMEOUT_SECONDS)
    try:
        payload, query_error = _http_get_json(client, url)
        if payload is None:
            return {
                "incidents": [],
                "sources": [{"id": "openfema", "title": "OpenFEMA Disaster Declarations", "url": url}],
                "error": f"fema_query_failed: {query_error}",
            }
        rows = payload.get("DisasterDeclarationsSummaries", [])
        incidents = [
            {
                "disaster_number": row.get("disasterNumber"),
                "type": row.get("incidentType"),
                "title": row.get("declarationTitle"),
                "declaration_date": row.get("declarationDate"),
            }
            for row in rows
        ]
        return {
            "incidents": incidents,
            "sources": [{"id": "openfema", "title": "OpenFEMA Disaster Declarations", "url": url}],
            "meta": {"retry_attempts": _RETRY_ATTEMPTS},
        }
    except Exception as exc:  # noqa: BLE001
        return {"incidents": [], "sources": [], "error": f"fema_lookup_failed: {exc}"}
    finally:
        client.close()


def search_sop_guidance(query: str, top_k: int = 3) -> dict[str, Any]:
    """Search local SOP snippets for grounding and return source references."""
    q = (query or "").lower().strip()
    if not q:
        return {"matches": [], "sources": [], "error": "Query is required."}

    if not _SOP_PATH.exists():
        return {"matches": [], "sources": [], "error": "SOP catalog is missing."}

    with _SOP_PATH.open("r", encoding="utf-8") as f:
        records = json.load(f)

    tokens = [t for t in q.split() if len(t) > 2]
    if not tokens:
        return {"matches": [], "sources": [], "error": "Query too short for SOP search."}
    scored = []
    for rec in records:
        haystack = f"{rec.get('title', '')} {rec.get('content', '')}".lower()
        score = sum(1 for tok in tokens if tok in haystack)
        if score > 0:
            scored.append((score, rec))

    scored.sort(key=lambda item: item[0], reverse=True)
    top = [item[1] for item in scored[: max(1, min(top_k, 10))]]
    matches = [{"title": rec["title"], "guidance": rec["content"]} for rec in top]
    sources = [
        {"id": rec["id"], "title": rec["title"], "url": f"local://sop/{rec['id']}"}
        for rec in top
    ]
    return {"matches": matches, "sources": sources}
