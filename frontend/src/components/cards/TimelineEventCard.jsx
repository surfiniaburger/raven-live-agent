function toneClass(eventType) {
  if (eventType === "tool") return "tone-tool";
  if (eventType === "result") return "tone-result";
  if (eventType === "source") return "tone-source";
  return "tone-text";
}

function eventMeta(parsed) {
  if (parsed.sources.length > 0) return { label: "Grounded Evidence", tone: "source" };
  if (parsed.toolResponses.length > 0) return { label: "Tool Result", tone: "result" };
  if (parsed.toolCalls.length > 0) return { label: "Tool Call", tone: "tool" };
  return { label: "Agent Narrative", tone: "text" };
}

function inferParts(parsed) {
  const lines = [];
  if (parsed.text) lines.push({ kind: "text", text: parsed.text });
  parsed.toolCalls.forEach((t) => {
    const args = t?.args && typeof t.args === "object" ? JSON.stringify(t.args) : "";
    lines.push({ kind: "tool", text: `tool: ${t.name}${args ? ` args=${args}` : ""}` });
  });
  parsed.toolResponses.forEach((r) => {
    const toolName = r?.name || "unknown_tool";
    lines.push({ kind: "result", text: `result: ${toolName}` });
    summarizeToolResponse(toolName, r?.response).forEach((line) => lines.push({ kind: line.kind, text: line.text }));
  });
  parsed.sources.forEach((s) =>
    lines.push({
      kind: "source",
      text: `source: ${s.id || "n/a"} | ${s.title || "untitled"}${s.url ? ` | ${s.url}` : ""}`,
    }),
  );
  return lines;
}

function summarizeToolResponse(toolName, response) {
  const res = response && typeof response === "object" ? response : {};
  const out = [];

  if (res.error) out.push({ kind: "result", text: `error: ${res.error}` });
  if (res.note) out.push({ kind: "result", text: `note: ${res.note}` });

  if (toolName === "fetch_weather_alerts") {
    const count = Array.isArray(res.alerts) ? res.alerts.length : 0;
    out.push({ kind: "result", text: `weather alerts: ${count}` });
    if (count > 0) {
      const first = res.alerts[0];
      const headline = first?.headline || first?.event || "active alert";
      out.push({ kind: "result", text: `top alert: ${headline}` });
    }
  }

  if (toolName === "fetch_nigeria_weather_advisory") {
    if (res.location) out.push({ kind: "result", text: `location: ${res.location}` });
    if (res.risk_level) out.push({ kind: "result", text: `nigeria weather risk: ${res.risk_level}` });
    if (Array.isArray(res.actions)) out.push({ kind: "result", text: `recommended actions: ${res.actions.length}` });
    if (res.advisory) out.push({ kind: "result", text: `advisory: ${String(res.advisory).slice(0, 220)}...` });
  }

  if (toolName === "fetch_weather_context") {
    if (res.route) out.push({ kind: "result", text: `weather route: ${res.route}` });
    if (res.location) out.push({ kind: "result", text: `location: ${res.location}` });
    if (res.risk_level) out.push({ kind: "result", text: `risk level: ${res.risk_level}` });
    if (Array.isArray(res.alerts)) out.push({ kind: "result", text: `alerts: ${res.alerts.length}` });
    if (Array.isArray(res.actions)) out.push({ kind: "result", text: `actions: ${res.actions.length}` });
    if (res.note) out.push({ kind: "result", text: `note: ${res.note}` });
    if (res.advisory) out.push({ kind: "result", text: `advisory: ${String(res.advisory).slice(0, 220)}...` });
  }

  if (toolName === "query_fema_incidents") {
    const count = Array.isArray(res.incidents) ? res.incidents.length : 0;
    out.push({ kind: "result", text: `fema incidents: ${count}` });
    if (count > 0) {
      const first = res.incidents[0];
      const title = first?.title || first?.type || "incident";
      out.push({ kind: "result", text: `latest incident: ${title}` });
    }
  }

  if (toolName === "search_sop_guidance") {
    const count = Array.isArray(res.matches) ? res.matches.length : 0;
    out.push({ kind: "result", text: `sop matches: ${count}` });
  }

  if (toolName === "search_incident_knowledge") {
    const confidence = res?.confidence?.overall;
    const recommendation = res?.confidence?.recommendation;
    const count = Array.isArray(res.results) ? res.results.length : 0;
    out.push({ kind: "result", text: `knowledge hits: ${count}` });
    if (typeof confidence === "number") {
      out.push({ kind: "result", text: `confidence: ${confidence.toFixed(2)}` });
    }
    if (recommendation) {
      out.push({ kind: "result", text: `gating: ${recommendation}` });
    }
  }

  if (toolName === "detect_hazard") {
    if (res.hazard_level) out.push({ kind: "result", text: `hazard level: ${res.hazard_level}` });
    if (Array.isArray(res.tags) && res.tags.length > 0) {
      out.push({ kind: "result", text: `hazard tags: ${res.tags.join(", ")}` });
    }
  }

  if (toolName === "generate_incident_brief" && res.next_steps) {
    out.push({ kind: "result", text: `next steps: ${res.next_steps}` });
  }

  return out;
}

export default function TimelineEventCard({ parsedEvent, index }) {
  const lines = inferParts(parsedEvent);
  const meta = eventMeta(parsedEvent);
  const isLatest = index === 0;

  return (
    <article
      className={`timeline-event ${isLatest ? "timeline-event-latest" : ""}`}
      style={{ animationDelay: `${Math.min(index * 55, 440)}ms` }}
    >
      <header className="timeline-meta">
        <span className={`timeline-pill tone-${meta.tone}`}>{meta.label}</span>
        <span className="timeline-step">Step {index + 1}</span>
      </header>
      {lines.map((line, idx) => (
        <p key={`${line.kind}-${idx}`} className={`timeline-line ${toneClass(line.kind)}`}>
          {line.text}
        </p>
      ))}
    </article>
  );
}
