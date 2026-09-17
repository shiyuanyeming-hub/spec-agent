export type Lang = "zh" | "ja" | "en";

export interface StageEvent {
  stage: "clarifier" | "structurer" | "validator" | "done";
  label: string;
  status: "start" | "ok" | "passed" | "needs_review" | "blocked";
  round: number;
  detail: string;
  duration_ms: number;
}

export interface UserStory {
  id: string;
  story: string;
  acceptance_criteria: string[];
}

export interface LangDoc {
  lang: Lang;
  title: string;
  background: string;
  goal: string;
  user_stories: UserStory[];
  functional_reqs: string[];
  nonfunctional_reqs: string[];
  risks: string[];
  open_questions: string[];
}

export interface GlossaryEntry {
  term_zh: string;
  term_en: string;
  term_ja: string;
  note: string;
}

export interface ValidationIssue {
  severity: "blocker" | "major" | "minor";
  category: string;
  message: string;
  suggestion: string;
}

export interface Clarifications {
  original: string;
  goal: string;
  target_users: string;
  success_metrics: string[];
  scope: string;
  assumptions: string[];
  open_questions: string[];
}

export type ValidationStatus = "passed" | "needs_review" | "blocked";

export interface ValidationResult {
  passed: boolean;
  status: ValidationStatus;
  summary: string;
  issues: ValidationIssue[];
  suggestions: string[];
  counts: { blocker: number; major: number; minor: number };
  structural_issues: number;
}

export interface GenerateResult {
  prd: {
    product_name: string;
    target_langs: Lang[];
    glossary: GlossaryEntry[];
    docs: Record<string, LangDoc>;
  };
  glossary: GlossaryEntry[];
  markdown: Record<string, string>;
  clarifications: Clarifications;
  validation: ValidationResult;
  rounds_used: number;
  status: ValidationStatus;
  stalled: boolean;
  provider: string;
  trace: StageEvent[];
}

export interface Meta {
  provider: string;
  model: string;
  supported_langs: Lang[];
  max_validation_rounds: number;
  max_input_chars: number;
  samples: { id: string; label: string; langs: Lang[]; text: string }[];
}

export async function fetchMeta(): Promise<Meta> {
  const resp = await fetch("/api/meta");
  if (!resp.ok) throw new Error(`加载配置失败：${resp.status}`);
  return resp.json();
}

export async function generate(rawText: string, targetLangs: Lang[]): Promise<GenerateResult> {
  const resp = await fetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ raw_text: rawText, target_langs: targetLangs }),
  });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail?.detail ? JSON.stringify(detail.detail) : `生成失败：${resp.status}`);
  }
  return resp.json();
}

interface StreamHandlers {
  onStage: (event: StageEvent) => void;
  onResult: (result: GenerateResult) => void;
  onError: (message: string) => void;
}

/** 消费后端 SSE 流：逐阶段回调进度，最后回调完整结果。 */
export async function generateStream(rawText: string, targetLangs: Lang[], handlers: StreamHandlers): Promise<void> {
  const resp = await fetch("/api/generate/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ raw_text: rawText, target_langs: targetLangs }),
  });
  if (!resp.ok || !resp.body) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail?.detail ? JSON.stringify(detail.detail) : `生成失败：${resp.status}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const eventLine = frame.split("\n").find((line) => line.startsWith("event:"));
      const dataLine = frame.split("\n").find((line) => line.startsWith("data:"));
      if (!dataLine) continue;
      const payload = JSON.parse(dataLine.slice(5).trim());
      if (eventLine?.includes("stage")) handlers.onStage(payload as StageEvent);
      else if (eventLine?.includes("result")) handlers.onResult(payload as GenerateResult);
      else if (eventLine?.includes("error")) handlers.onError(payload.message ?? "未知错误");
    }
  }
}
