import type { Clarifications } from "@/lib/api";

function List({ items, ordered = false }: { items: string[]; ordered?: boolean }) {
  if (!items || items.length === 0) return <p className="hint">—</p>;
  const Tag = ordered ? "ol" : "ul";
  return (
    <Tag className="plain">
      {items.map((item, index) => (
        <li key={index}>{item}</li>
      ))}
    </Tag>
  );
}

export default function ClarificationPanel({ clarifications }: { clarifications: Clarifications }) {
  return (
    <div>
      <h3 style={{ marginTop: 0 }}>目标</h3>
      <p>{clarifications.goal || "—"}</p>
      <h3>目标用户</h3>
      <p>{clarifications.target_users || "—"}</p>
      <h3>范围</h3>
      <p>{clarifications.scope || "—"}</p>
      <h3>成功指标</h3>
      <List items={clarifications.success_metrics} />
      <h3>显式假设（需要需求方确认后才算数）</h3>
      <List items={clarifications.assumptions} />
      <h3>待确认问题</h3>
      <List items={clarifications.open_questions} ordered />
    </div>
  );
}
