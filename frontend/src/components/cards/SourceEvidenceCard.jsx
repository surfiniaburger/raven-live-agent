export default function SourceEvidenceCard({ sources }) {
  const rows = Array.isArray(sources) ? sources : [];

  return (
    <article className="command-card source-card">
      <header className="card-header">
        <h3 className="card-title">Source Evidence</h3>
        <span className="count-pill">{rows.length}</span>
      </header>

      {rows.length === 0 ? (
        <p className="empty-state">No grounded sources in timeline yet.</p>
      ) : (
        <ul className="source-list">
          {rows.map((src, idx) => (
            <li key={`${src.id || "src"}-${idx}`} className="source-row">
              <span className="source-id">{src.id || "n/a"}</span>
              <span className="source-title">{src.title || "Untitled source"}</span>
              {src.url ? (
                <a className="source-link" href={src.url} target="_blank" rel="noreferrer">
                  open
                </a>
              ) : (
                <span className="source-link muted">none</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}
