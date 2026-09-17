import type { StageEvent } from "@/lib/api";

const ICONS: Record<string, string> = {
  start: "…",
  ok: "✓",
  passed: "✓",
  needs_review: "!",
  blocked: "✗",
};

const TONE: Record<string, string> = {
  start: "run",
  ok: "ok",
  passed: "ok",
  needs_review: "warn",
  blocked: "bad",
};

export default function StageTimeline({ events }: { events: StageEvent[] }) {
  if (events.length === 0) {
    return <p className="hint">运行后会在这里逐步显示三个 Agent 的进度。</p>;
  }
  return (
    <ul className="timeline">
      {events.map((event, index) => (
        <li key={`${event.stage}-${event.round}-${event.status}-${index}`}>
          <span className={`dot ${TONE[event.status] ?? ""}`}>{ICONS[event.status] ?? "·"}</span>
          <span>
            <span className="label">
              {event.label}
              {event.round > 0 ? ` · 第 ${event.round} 轮` : ""}
            </span>
            {event.detail ? <span className="detail" style={{ display: "block" }}>{event.detail}</span> : null}
          </span>
          <span className="hint mono">{event.duration_ms ? `${(event.duration_ms / 1000).toFixed(1)}s` : ""}</span>
        </li>
      ))}
    </ul>
  );
}
