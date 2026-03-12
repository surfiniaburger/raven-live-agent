import { useEffect, useMemo, useRef, useState } from 'react';
import { useGeminiSocket } from '../hooks/useGeminiSocket';
import ConnectionStatusCard from './cards/ConnectionStatusCard';
import IncidentSummaryCard from './cards/IncidentSummaryCard';
import SourceEvidenceCard from './cards/SourceEvidenceCard';
import TimelineEventCard from './cards/TimelineEventCard';

function parseEvents(event) {
  const out = { text: '', toolCalls: [], toolResponses: [], sources: [] };
  if (!event) return out;

  const parts = event.serverContent?.modelTurn?.parts || event.content?.parts || [];
  for (const part of parts) {
    if (part.text) out.text += part.text;
    if (part.functionCall) out.toolCalls.push(part.functionCall);
    if (part.functionResponse) out.toolResponses.push(part.functionResponse);
    if (part.functionResponse?.response?.sources && Array.isArray(part.functionResponse.response.sources)) {
      out.sources.push(...part.functionResponse.response.sources);
    }
  }
  out.sources.push(...parseSourcesFromText(out.text));
  return out;
}

function parseSourcesFromText(text) {
  if (!text || !text.includes('Sources:')) return [];
  const lines = text.split('\n').map((line) => line.trim()).filter(Boolean);
  const start = lines.findIndex((line) => line.toLowerCase().startsWith('sources:'));
  if (start === -1) return [];
  const sourceLines = lines.slice(start + 1).filter((line) => line.startsWith('-') || line.startsWith('*') || line.startsWith('['));
  return sourceLines.map((line, idx) => ({ id: `text-${idx + 1}`, title: line.replace(/^[-*]\s*/, ''), url: '' }));
}

function deriveIncidentState(events) {
  const state = {
    hazardLevel: 'UNKNOWN',
    tags: [],
    summary: 'No brief generated yet.',
    actions: 'No actions captured yet.',
    sources: [],
  };

  for (const evt of events) {
    const parsed = parseEvents(evt);
    for (const resp of parsed.toolResponses) {
      const toolName = resp.name || '';
      const payload = resp.response || {};
      if (toolName === 'detect_hazard' && payload.hazard_level) {
        state.hazardLevel = payload.hazard_level;
        state.tags = Array.isArray(payload.tags) ? payload.tags : [];
      }
      if (toolName === 'generate_incident_brief') {
        state.summary = payload.summary || state.summary;
        state.actions = payload.actions || state.actions;
      }
    }
    if (parsed.sources.length > 0) {
      state.sources = dedupeSources([...state.sources, ...parsed.sources]).slice(0, 8);
    }
  }

  return state;
}

function dedupeSources(sources) {
  const seen = new Set();
  const out = [];
  for (const s of sources) {
    const key = `${s.id || ''}|${s.title || ''}|${s.url || ''}`;
    if (!seen.has(key)) {
      seen.add(key);
      out.push(s);
    }
  }
  return out;
}

export default function LiveOpsConsole() {
  const videoRef = useRef(null);
  const [events, setEvents] = useState([]);
  const [mode, setMode] = useState("LIVE");
  const [systemAlerts, setSystemAlerts] = useState([]);
  const sessionId = useMemo(() => Math.random().toString(36).slice(2), []);
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const configuredWsBase = import.meta.env.VITE_WS_BASE_URL;
  const wsBase = configuredWsBase || `${protocol}//${window.location.host}`;
  const wsUrl = `${wsBase}/ws/ops-user/${sessionId}`;

  const { status, lastMessage, connect, disconnect, startStream, stopStream } = useGeminiSocket(wsUrl);

  const start = async () => {
    connect();
    await startStream(videoRef.current);
  };

  const stop = () => {
    stopStream();
    disconnect();
  };

  useEffect(() => {
    const parsed = parseEvents(lastMessage);
    if (!lastMessage || (!parsed.text && parsed.toolCalls.length === 0 && parsed.toolResponses.length === 0)) return;
    setEvents((prev) => [lastMessage, ...prev].slice(0, 15));

    if (parsed.text && parsed.text.includes("[SYSTEM:MODE_SWITCH]")) {
      const match = parsed.text.match(/mode=([a-zA-Z]+)/);
      if (match) {
        setMode(match[1].toUpperCase());
      }
    }

    if (parsed.text && parsed.text.includes("[SYSTEM:")) {
      setSystemAlerts((prev) => {
        const next = [parsed.text, ...prev].slice(0, 4);
        return next;
      });
    }
  }, [lastMessage]);

  const incident = useMemo(() => deriveIncidentState(events), [events]);

  return (
    <div className="command-shell">
      <section className="command-main">
        <header className="command-header">
          <div>
            <p className="eyebrow">Live Operations</p>
            <div className="title-row">
              <h1 className="command-title">RAVEN Emergency Command</h1>
              <span className={`status-chip status-${mode === "FALLBACK" ? "warn" : "ok"}`}>
                {mode}
              </span>
            </div>
          </div>
          <ConnectionStatusCard status={status} />
        </header>
        {systemAlerts.length > 0 && (
          <section className="system-alerts" aria-live="polite">
            {systemAlerts.map((alert, idx) => (
              <p key={`${alert}-${idx}`} className="system-alert">
                {alert.replace("[SYSTEM:", "").replace("]", "")}
              </p>
            ))}
          </section>
        )}

        <div className="camera-stage">
          <video ref={videoRef} muted playsInline className="camera-feed" />
          <div className="camera-overlay" aria-hidden="true">
            <div className="scanline scanline-top" />
            <div className="scanline scanline-bottom" />
            <div className="corner corner-tl" />
            <div className="corner corner-tr" />
            <div className="corner corner-bl" />
            <div className="corner corner-br" />
          </div>
          <div className="camera-hud">
            <span className="hud-live">LIVE FEED</span>
            <span className="hud-metric">Hazard {incident.hazardLevel || "UNKNOWN"}</span>
            <span className="hud-metric">Sources {incident.sources.length}</span>
          </div>
        </div>

        <div className="action-dock" role="group" aria-label="Session controls">
          <button onClick={start} className="action-btn action-btn-primary">Start Live Session</button>
          <button onClick={stop} className="action-btn action-btn-danger">Stop Session</button>
        </div>
      </section>

      <aside className="command-side">
        <IncidentSummaryCard incident={incident} />
        <SourceEvidenceCard sources={incident.sources} />

        <section className="command-card timeline-card">
          <header className="card-header">
            <h2 className="card-title">Timeline</h2>
            <span className="count-pill">{events.length}</span>
          </header>
          {events.length === 0 && <p className="text-slate-400">No events yet.</p>}
          {events.map((evt, idx) => {
            const p = parseEvents(evt);
            return <TimelineEventCard key={idx} parsedEvent={p} index={idx} />;
          })}
        </section>
      </aside>
    </div>
  );
}
