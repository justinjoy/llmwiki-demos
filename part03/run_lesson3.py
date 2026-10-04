#!/usr/bin/env python3
"""3교시: 원문 포함 → CLI 실행 → 후보 사실·별칭·개체·검토 제안 저장."""
import argparse
import json
from pathlib import Path
import sys
import run_prompt
from validate_assertions import load_docs, validate

LESSON = Path(__file__).resolve().parent
RAW = [LESSON / "raw" / name for name in ("ARCH-01_v1.md", "ADR-07_v1.md", "INC-03_v1.md", "GLOSS-01_v1.md", "ARCH-01_v2.md")]
ONTOLOGY = [LESSON / "ontology" / name for name in ("types.csv", "relations.csv")]
TASKS = {
    "extract": ("prompt.txt", "assertions.jsonl", []),
    "aliases": ("prompts/aliases.txt", "aliases.json", []),
    "entities": ("prompts/entities.txt", "entities.json", ["assertions.jsonl", "aliases.json"]),
    "review": ("prompts/review.txt", "review_suggestions.md", ["assertions.jsonl", "aliases.json", "entities.json", "error_candidates.json"]),
}


def validate_output(task):
    path = LESSON / TASKS[task][1]
    if task == "extract":
        errors = validate(path, "pending")
        if errors:
            raise ValueError("후보 검사 실패:\n" + "\n".join(errors))
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if {r["assertion_id"] for r in rows} != {"F01", "F02", "F03"}:
            raise ValueError("직접 호출 후보 F01, F02, F03이 필요합니다.")
        return
    if task == "review":
        text = path.read_text(encoding="utf-8")
        if any(ident not in text for ident in ["F01", "F02", "F03", *[f"E{i:02}" for i in range(1, 7)]]):
            raise ValueError("검토 제안에 F01~F03과 E01~E06을 모두 포함하세요.")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    if task == "aliases":
        groups = [(data, ["alias", "canonical_id"], "alias")]
    else:
        if not isinstance(data, dict):
            raise ValueError("entities.json은 JSON 객체여야 합니다.")
        groups = [(data.get("services"), ["id", "type", "owner_team"], "id"),
                  (data.get("apis"), ["id", "type", "owner_service", "method", "path", "caller"], "id"),
                  (data.get("excluded_from_service_graph"), ["id", "type", "reason"], "id")]
    docs = load_docs()
    for rows, fields, key in groups:
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"{path.name}: 비어 있지 않은 결과 배열이 필요합니다.")
        seen = set()
        for row in rows:
            required = fields + ["source_id", "version", "section", "quote"]
            if not isinstance(row, dict) or any(not isinstance(row.get(f), str) or not row[f].strip() for f in required):
                raise ValueError(f"{path.name}: 필수 문자열 필드를 확인하세요: {required}")
            if row[key] in seen:
                raise ValueError(f"{path.name}: 중복 ID 또는 별칭: {row[key]}")
            seen.add(row[key])
            doc = docs.get(row["source_id"] + ":" + row["version"])
            if not doc or row["quote"] not in doc["sections"].get(row["section"], ""):
                raise ValueError(f"{path.name}: {row[key]}의 문서 번호·버전·절·인용을 확인하세요.")
            if "owner_service" in fields:
                timeout = row.get("timeout_seconds")
                if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout < float("inf"):
                    raise ValueError(f"{path.name}: {row[key]}의 timeout_seconds는 양수여야 합니다.")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cli", required=True)
    p.add_argument("--task", choices=[*TASKS, "all"], default="extract")
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
                for dependency in TASKS:
                    if TASKS[dependency][1] in extra:
                        validate_output(dependency)
                for rel in extra:
                    text = (LESSON / rel).read_text(encoding="utf-8")
                    if "TODO" in text:
                        raise ValueError(f"선행 실습을 먼저 완료하세요: {rel}")
            print(f"\n3교시 / {task}", flush=True)
            params = argparse.Namespace(**vars(args))
            params.prompt = str(LESSON / prompt)
            params.context = [str(f) for f in RAW + ONTOLOGY + [LESSON / rel for rel in extra]]
            params.output = str(LESSON / output)
            params.log_dir = str(LESSON / "runs")
            result = run_prompt.execute(params)
            if result:
                return result
            if not args.dry_run:
                validate_output(task)
                if task == "extract":
                    from review_workflow import Store
                    store = Store(LESSON)
                    if store.db.exists():
                        changed = store.sync("LLM 재추출: " + args.cli, "추출 결과 변경으로 재검토 요청")
                        if changed:
                            print("새 후보 버전(pending): " + ", ".join(changed), flush=True)
                print(f"검사 통과: {output}", flush=True)
        if args.dry_run and args.task == "all":
            print("전체 미리보기는 현재 파일을 사용합니다. 실제 순차 실행에서는 앞 단계의 생성 결과를 다음 입력에 포함합니다.")
        return 0
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
