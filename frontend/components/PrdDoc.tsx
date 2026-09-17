import type { Lang, LangDoc } from "@/lib/api";

const LANG_LABEL: Record<Lang, string> = { zh: "中文", ja: "日本語", en: "English" };

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

export function LangTabs({
  langs,
  active,
  onChange,
}: {
  langs: Lang[];
  active: Lang;
  onChange: (lang: Lang) => void;
}) {
  return (
    <div className="tabs">
      {langs.map((lang) => (
        <button key={lang} className={`tab ${lang === active ? "active" : ""}`} onClick={() => onChange(lang)}>
          {LANG_LABEL[lang] ?? lang}
        </button>
      ))}
    </div>
  );
}

export function PrdDoc({ doc }: { doc: LangDoc }) {
  return (
    <div>
      <h2>{doc.title}</h2>
      <h3>背景</h3>
      <p>{doc.background || "—"}</p>
      <h3>目标</h3>
      <p>{doc.goal || "—"}</p>
      <h3>用户故事</h3>
      {(doc.user_stories ?? []).length === 0 ? (
        <p className="hint">—</p>
      ) : (
        doc.user_stories.map((story) => (
          <div className="story" key={story.id}>
            <div className="story-head">
              <span className="story-id">{story.id}</span>
              <span>{story.story}</span>
            </div>
            <ul className="ac">
              {(story.acceptance_criteria ?? []).map((ac, index) => (
                <li key={index}>{ac}</li>
              ))}
            </ul>
          </div>
        ))
      )}
      <h3>功能需求</h3>
      <List items={doc.functional_reqs} />
      <h3>非功能需求</h3>
      <List items={doc.nonfunctional_reqs} />
      <h3>风险</h3>
      <List items={doc.risks} />
      <h3>待确认问题</h3>
      <List items={doc.open_questions} ordered />
    </div>
  );
}
