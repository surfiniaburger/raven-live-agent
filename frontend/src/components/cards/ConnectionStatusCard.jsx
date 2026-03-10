const STATUS_CONFIG = {
  CONNECTED: { label: "CONNECTED", tone: "ok" },
  DISCONNECTED: { label: "DISCONNECTED", tone: "muted" },
  ERROR: { label: "ERROR", tone: "danger" },
};

export default function ConnectionStatusCard({ status }) {
  const cfg = STATUS_CONFIG[status] || { label: status || "UNKNOWN", tone: "muted" };

  return (
    <div className="command-card status-card">
      <div className="status-card-row">
        <span className="eyebrow">Link</span>
        <span className={`status-chip status-${cfg.tone}`}>{cfg.label}</span>
      </div>
      <p className="status-help">
        {cfg.tone === "ok" ? "Live telemetry route is active." : "Reconnect to resume live telemetry."}
      </p>
    </div>
  );
}
