"""本地冒烟：跑完整流水线并打印/保存多语种 PRD。

用法：
    python scripts/smoke.py                                  # 用内置示例 + 当前配置的 LLM
    python scripts/smoke.py "你的需求描述" --langs zh,ja,en
    python scripts/smoke.py --sample b2b-export --out docs/example-output.md
"""
import argparse
import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings  # noqa: E402
from app.pipeline import run_pipeline  # noqa: E402
from app.samples import DEMO_REQUIREMENT, SAMPLES  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Spec Agent 冒烟脚本")
    parser.add_argument("text", nargs="?", default=None, help="需求描述（缺省用 --sample 或内置示例）")
    parser.add_argument("--sample", default=None, help=f"内置示例 id：{', '.join(s['id'] for s in SAMPLES)}")
    parser.add_argument("--langs", default="zh,ja,en", help="输出语种，逗号分隔（zh,ja,en）")
    parser.add_argument("--rounds", type=int, default=None, help="最大校验轮次（默认取配置）")
    parser.add_argument("--out", default=None, help="把 Markdown 结果写到该文件（多语种用 -zh/-ja/-en 后缀）")
    return parser.parse_args()


def resolve_text(args: argparse.Namespace) -> str:
    if args.text:
        return args.text
    if args.sample:
        for sample in SAMPLES:
            if sample["id"] == args.sample:
                return sample["text"]
        raise SystemExit(f"未知示例 id：{args.sample}")
    return DEMO_REQUIREMENT


async def main() -> int:
    args = parse_args()
    text = resolve_text(args)
    langs = [code.strip() for code in args.langs.split(",") if code.strip()]

    print(f"LLM provider : {settings.llm_provider} ({settings.llm_model})")
    print(f"target langs : {', '.join(langs)}")
    print(f"input        : {text[:80]}{'…' if len(text) > 80 else ''}\n")

    result = await run_pipeline(text, langs, max_rounds=args.rounds)

    for event in result.trace:
        mark = {"ok": "✓", "start": "…", "passed": "✓", "failed": "✗", "needs_review": "!"}.get(event["status"], "·")
        print(f"  {mark} [{event['round']}] {event['stage']:<11} {event['status']:<12} {event['detail'][:70]}")

    print(f"\n校验结果：{'通过' if result.validation.passed else '未通过'}（{result.rounds_used} 轮）— {result.validation.summary}")
    for issue in result.validation.issues[:5]:
        print(f"  - [{issue['severity']}/{issue['category']}] {issue['message']}")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        if len(langs) == 1:
            out.write_text(result.markdown[langs[0]], encoding="utf-8")
            print(f"\n已写入 {out}")
        else:
            for code in langs:
                target = out.with_name(f"{out.stem}.{code}{out.suffix}")
                target.write_text(result.markdown[code], encoding="utf-8")
                print(f"已写入 {target}")
    else:
        print("\n" + "=" * 72 + f"\n{result.markdown[langs[0]]}")

    return 0 if result.validation.passed else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
