"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import ClarificationPanel from "@/components/ClarificationPanel";
import GlossaryTable from "@/components/GlossaryTable";
import { LangTabs, PrdDoc } from "@/components/PrdDoc";
import StageTimeline from "@/components/StageTimeline";
import ValidationPanel from "@/components/ValidationPanel";
import { fetchMeta, generate, generateStream } from "@/lib/api";
import type { GenerateResult, Lang, Meta, StageEvent } from "@/lib/api";

const LANG_LABEL: Record<Lang, string> = { zh: "简体中文", ja: "日本語", en: "English" };

export default function Home() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [text, setText] = useState("");
  const [langs, setLangs] = useState<Lang[]>(["zh", "ja", "en"]);
  const [running, setRunning] = useState(false);
  const [stages, setStages] = useState<StageEvent[]>([]);
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [error, setError] = useState("");
  const [activeLang, setActiveLang] = useState<Lang>("zh");
  const resultRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchMeta()
      .then((data) => {
        setMeta(data);
        setText((current) => current || data.samples[0]?.text || "");
      })
      .catch(() => setError("无法连接后端 API（默认 http://localhost:8000），请先启动后端。"));
  }, []);

  const canSubmit = useMemo(() => text.trim().length >= 10 && langs.length > 0 && !running, [text, langs, running]);

  function toggleLang(lang: Lang) {
    setLangs((current) => (current.includes(lang) ? current.filter((item) => item !== lang) : [...current, lang]));
  }

  async function onSubmit() {
    setRunning(true);
    setError("");
    setResult(null);
    setStages([]);
    try {
      await generateStream(text.trim(), langs, {
        onStage: (event) => setStages((current) => [...current, event]),
        onResult: (data) => {
          setResult(data);
          setActiveLang(data.prd.target_langs[0] ?? "zh");
          setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
        },
        onError: (message) => setError(message),
      });
    } catch {
      // 流式接口不可用时退回一次性接口
      try {
        const data = await generate(text.trim(), langs);
        setResult(data);
        setStages(data.trace);
        setActiveLang(data.prd.target_langs[0] ?? "zh");
      } catch (fallbackError) {
        setError(fallbackError instanceof Error ? fallbackError.message : "生成失败");
      }
    } finally {
      setRunning(false);
    }
  }

  function downloadMarkdown() {
    if (!result) return;
    const blob = new Blob([result.markdown[activeLang] ?? ""], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${result.prd.product_name || "PRD"}.${activeLang}.md`;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function copyMarkdown() {
    if (!result) return;
    await navigator.clipboard.writeText(result.markdown[activeLang] ?? "");
  }

  const doc = result?.prd.docs[activeLang];

  return (
    <main className="page">
      <div className="topbar">
        <div className="brand">
          <div className="brand-mark">SA</div>
          <div>
            <h1>Spec Agent · 多语种 PRD 生成</h1>
            <p>模糊需求 → 澄清 → 结构化 PRD（中文 / 日本語 / English）→ 质量校验</p>
          </div>
        </div>
        <div className="badges">
          {meta ? (
            <>
              <span className={`badge ${meta.provider === "fake" ? "warn" : "accent"}`}>
                {meta.provider === "fake" ? "Mock 模式（未配置 API key）" : `模型 ${meta.model}`}
              </span>
              <span className="badge">最多 {meta.max_validation_rounds} 轮校验</span>
            </>
          ) : (
            <span className="badge">连接后端中…</span>
          )}
        </div>
      </div>

      <div className="layout">
        <section>
          <div className="card">
            <h2>1 · 写下你的需求</h2>
            <p className="hint">不用写得很规整，用任意语言说清"想要解决什么问题"即可。</p>
            <textarea
              value={text}
              maxLength={meta?.max_input_chars ?? 4000}
              onChange={(event) => setText(event.target.value)}
              placeholder="例如：日本市场想要一个能让老年用户更容易用的支付流程，大概下个季度要。"
            />
            <div className="chips">
              {(meta?.samples ?? []).map((sample) => (
                <button
                  key={sample.id}
                  className="chip"
                  onClick={() => {
                    setText(sample.text);
                    setLangs(sample.langs);
                  }}
                >
                  {sample.label}
                </button>
              ))}
            </div>
            <div className="langs">
              {(["zh", "ja", "en"] as Lang[]).map((lang) => (
                <label key={lang}>
                  <input type="checkbox" checked={langs.includes(lang)} onChange={() => toggleLang(lang)} />
                  {LANG_LABEL[lang]}
                </label>
              ))}
            </div>
            <div className="actions">
              <button className="primary" disabled={!canSubmit} onClick={onSubmit}>
                {running ? "生成中…" : "生成 PRD"}
              </button>
              <span className="hint">
                {text.trim().length} 字符 · {langs.length} 个语种
              </span>
            </div>
            {error ? <div className="error">{error}</div> : null}
          </div>

          <div className="card">
            <h2>2 · 流水线进度</h2>
            <StageTimeline events={stages} />
          </div>

          {result ? (
            <div className="card" ref={resultRef}>
              <h2>3 · 澄清结论</h2>
              <ClarificationPanel clarifications={result.clarifications} />
              <p className="hint">
                共迭代 {result.rounds_used} 轮{result.stalled ? "（问题数不再下降，已提前停止）" : ""} · 生成模式 {result.provider}
              </p>
            </div>
          ) : null}
        </section>

        <section>
          {result && doc ? (
            <>
              <div className="card">
                <h2>
                  4 · 多语种 PRD
                  <span className="hint" style={{ fontWeight: 400 }}>
                    {result.prd.product_name}
                  </span>
                </h2>
                <LangTabs langs={result.prd.target_langs} active={activeLang} onChange={setActiveLang} />
                <PrdDoc doc={doc} />
                <div className="actions">
                  <button onClick={copyMarkdown}>复制本语种 Markdown</button>
                  <button onClick={downloadMarkdown}>下载 .md</button>
                </div>
              </div>

              <div className="card">
                <h2>5 · 术语对照表</h2>
                <GlossaryTable glossary={result.glossary} />
              </div>

              <div className="card">
                <h2>6 · 校验报告</h2>
                <ValidationPanel validation={result.validation} />
              </div>
            </>
          ) : (
            <div className="empty">
              <p style={{ marginTop: 0, fontSize: 16, color: "var(--text)" }}>左侧输入一段需求，流水线会这样跑：</p>
              <div className="steps">
                <div className="step">
                  <b>① Clarifier 需求澄清</b>
                  <span>抽出目标、人群、成功指标、范围；信息不足的部分显式标注为假设与待确认问题。</span>
                </div>
                <div className="step">
                  <b>② Structurer 结构化</b>
                  <span>按选定语种产出完整 PRD：用户故事 + 可测试验收标准 + 术语对照表。</span>
                </div>
                <div className="step">
                  <b>③ Validator 质量校验</b>
                  <span>确定性结构校验（语种/故事/AC 一致性）+ LLM 语义校验（INVEST、可测试性、三语等价），问题回注上一步迭代。</span>
                </div>
              </div>
            </div>
          )}
        </section>
      </div>

      <p className="footer">
        Spec Agent · MIT License · 与 <a href="https://github.com/shiyuanyeming-hub/voc-agent">VoC Agent</a> 同系列（用户声音 →
        开发交付）
      </p>
    </main>
  );
}
