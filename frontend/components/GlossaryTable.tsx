import type { GlossaryEntry, Lang } from "@/lib/api";

const LANG_LABEL: Record<Lang, string> = { zh: "中文", ja: "日本語", en: "English" };

export default function GlossaryTable({ glossary }: { glossary: GlossaryEntry[] }) {
  if (!glossary || glossary.length === 0) {
    return <p className="hint">本次没有生成术语对照表。</p>;
  }
  return (
    <table>
      <thead>
        <tr>
          <th>中文</th>
          <th>English</th>
          <th>日本語</th>
          <th>说明</th>
        </tr>
      </thead>
      <tbody>
        {glossary.map((entry, index) => (
          <tr key={index}>
            <td>{entry.term_zh}</td>
            <td>{entry.term_en}</td>
            <td>{entry.term_ja}</td>
            <td>{entry.note}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export { LANG_LABEL };
