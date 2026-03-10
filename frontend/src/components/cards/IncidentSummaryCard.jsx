function severityTone(level) {
  const normalized = String(level || "").toLowerCase();
  if (normalized.includes("high") || normalized.includes("critical")) return "danger";
  if (normalized.includes("med") || normalized.includes("warn")) return "warn";
  if (normalized.includes("low")) return "ok";
  return "muted";
}

export default function IncidentSummaryCard({ incident }) {
  const hazardTone = severityTone(incident?.hazardLevel);
  const tagsText = incident?.tags?.length ? incident.tags.join(", ") : "No tags yet";

  return (
    <article className="command-card incident-card">
      <header className="card-header">
        <h3 className="card-title">Incident Summary</h3>
        <span className={`status-chip status-${hazardTone}`}>{incident?.hazardLevel || "UNKNOWN"}</span>
      </header>
      <p className="card-body">
        <span className="field-label">Tags:</span> {tagsText}
      </p>
      <p className="card-body">
        <span className="field-label">Summary:</span> {incident?.summary || "No brief generated yet."}
      </p>
      <p className="card-body">
        <span className="field-label">Actions:</span> {incident?.actions || "No actions captured yet."}
      </p>
    </article>
  );
}
