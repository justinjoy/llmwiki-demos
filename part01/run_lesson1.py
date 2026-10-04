#!/usr/bin/env python3
"""1교시: 원문 포함 → CLI 실행 → 위키/탐색 기록 저장."""
import argparse
from pathlib import Path
import sys
import run_prompt

LESSON = Path(__file__).resolve().parent
RAW = [LESSON / "raw" / name for name in ("ARCH-01_v1.md", "ADR-07_v1.md", "INC-03_v1.md")]
TASKS = {
    "pay": ("prompt.txt", "wiki/services/pay.md", []),
    "order": ("prompts/order.txt", "wiki/services/order.md", ["wiki/services/pay.md"]),
    "incident": ("prompts/incident.txt", "wiki/incidents/INC-03.md", []),
    "index": ("prompts/index.txt", "wiki/index.md", ["wiki/services/pay.md", "wiki/services/order.md", "wiki/incidents/INC-03.md"]),
    "explore": ("prompts/explore.txt", "exploration.csv", ["wiki/index.md", "wiki/services/order.md", "wiki/services/pay.md", "wiki/incidents/INC-03.md"]),
    "log": ("prompts/log.txt", "wiki/log.md", ["wiki/services/pay.md", "wiki/services/order.md", "wiki/incidents/INC-03.md", "exploration.csv"]),
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cli", required=True)
    p.add_argument("--task", choices=[*TASKS, "all"], default="pay")
    p.add_argument("--mode", choices=["auto", "print", "codex"], default="auto")
    p.add_argument("--cli-arg", action="append", default=[])
    p.add_argument("--timeout", type=float, default=300)
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    tasks = list(TASKS) if args.task == "all" else [args.task]
    # Check all destinations before starting any billed request.
    if not args.overwrite and not args.dry_run:
        existing = [TASKS[t][1] for t in tasks if (LESSON / TASKS[t][1]).exists()]
        if existing:
            p.error("배포 템플릿 또는 기존 결과" + "가 있습니다. --overwrite를 지정하면 실행 기록에 백업 후 교체합니다: " + ", ".join(existing))
    try:
        for task in tasks:
            prompt, output, extra = TASKS[task]
            if not args.dry_run:
                for rel in extra:
                    text = (LESSON / rel).read_text(encoding="utf-8")
                    if "TODO" in text:
                        raise ValueError(f"선행 실습을 먼저 완료하세요: {rel}")
            print(f"\n1교시 / {task}", flush=True)
            params = argparse.Namespace(**vars(args))
            params.prompt = str(LESSON / prompt)
            params.context = [str(f) for f in RAW + [LESSON / rel for rel in extra]]
            params.output = str(LESSON / output)
            params.log_dir = str(LESSON / "runs")
            result = run_prompt.execute(params)
            if result:
                return result
        if args.dry_run and args.task == "all":
            print("전체 미리보기는 현재 파일을 사용합니다. 실제 순차 실행에서는 앞 단계의 생성 결과를 다음 입력에 포함합니다.")
        return 0
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
