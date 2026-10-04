"""원문 절·타입·상태 검사. 호출 방향과 의미는 사람이 확인합니다."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
REQUIRED = {"assertion_id", "subject", "predicate", "object", "subject_type", "object_type",
            "source_id", "version", "section", "quote", "document_status", "scope",
            "review_status", "reviewer", "snapshot_id"}


def load_docs():
    docs = {}
    for file in (ROOT / "raw").glob("*.md"):
        text = file.read_text(encoding="utf-8")
        ident = re.search(r"^문서 번호: (\S+) (v\d+)", text, re.M)
        state = re.search(r"^상태: (.+)$", text, re.M)
        if not ident or not state:
            raise ValueError(f"원문 메타데이터 누락: {file.name}")
        sections = {}
        headers = list(re.finditer(r"^## (\d+)\. [^\n]+\n", text, re.M))
        for i, header in enumerate(headers):
            end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
            sections["§" + header.group(1)] = text[header.end():end].strip()
        status = {"승인 완료": "approved", "검토 중": "draft", "검토 완료": "reviewed", "리뷰 완료": "reviewed"}.get(state.group(1).strip(), state.group(1).strip())
        docs[ident.group(1) + ":" + ident.group(2)] = {"status": status, "sections": sections}
    return docs


def validate(path, expected_status=None):
    docs = load_docs()
    errors, seen, count = [], set(), 0
    for number, line in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        count += 1
        try:
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("JSON 객체가 필요합니다.")
            missing = REQUIRED - row.keys()
            if missing:
                raise ValueError("필드 누락: " + ",".join(sorted(missing)))
            if any(not isinstance(row[key], str) for key in REQUIRED):
                raise ValueError("필수 필드는 문자열이어야 합니다.")
            if not row["assertion_id"].strip() or row["assertion_id"] in seen:
                raise ValueError("비어 있거나 중복된 assertion_id")
            seen.add(row["assertion_id"])
            if row["subject"] not in {"shop", "order", "pay", "ledger", "notify"} or row["object"] not in {"shop", "order", "pay", "ledger", "notify"}:
                raise ValueError("알 수 없는 Service ID")
            if row["subject_type"] != "Service" or row["object_type"] != "Service":
                raise ValueError("직접 관계는 Service 간 호출이어야 합니다.")
            if row["predicate"] != "depends_on" or row["snapshot_id"] != "S1":
                raise ValueError("이번 입력은 S1의 depends_on 관계입니다.")
            doc = docs.get(row["source_id"] + ":" + row["version"])
            if doc is None:
                raise ValueError("원문 버전 없음")
            if row["document_status"] != doc["status"]:
                raise ValueError("원문 문서 상태와 document_status가 다릅니다.")
            quote = row["quote"]
            if not quote.strip() or quote not in doc["sections"].get(row["section"], ""):
                raise ValueError("해당 원문 절에서 quote를 찾을 수 없습니다.")
            status = row["review_status"]
            if status not in {"pending", "approved", "rejected", "held"}:
                raise ValueError("알 수 없는 검토 상태")
            if expected_status and status != expected_status:
                raise ValueError(f"이 파일은 {expected_status} 상태여야 합니다.")
            if status == "pending" and row["reviewer"].strip():
                raise ValueError("미검토 후보에 검토자가 지정되어 있습니다.")
            if status == "approved" and (doc["status"] != "approved" or not row["reviewer"].strip()):
                raise ValueError("승인 문서와 실제 검토자 기록이 필요합니다.")
        except (ValueError, TypeError, KeyError) as exc:
            errors.append(f"{number}행: {exc}")
    if not count:
        errors.append("레코드가 없습니다.")
    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path")
    parser.add_argument("--status", choices=["pending", "approved"])
    args = parser.parse_args()
    try:
        errors = validate(args.path, args.status)
    except (OSError, ValueError) as exc:
        errors = [str(exc)]
    print("\n".join(errors) if errors else "구조·원문 인용 검사 통과. 관계 방향과 의미는 사람이 검토하세요.")
    raise SystemExit(bool(errors))
