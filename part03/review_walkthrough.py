"""Demonstrate CSV editing, import, correction and re-review in an isolated example."""
import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import shutil
import tempfile

from review_workflow import ROOT, Store, FIELDS, verify_export_file

ACTOR = '교육용 시연(실제 운영 승인 아님)'


def read_sheet(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != FIELDS:
            raise ValueError('CSV의 열 이름과 순서를 유지하세요.')
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError('CSV 열 수를 확인하세요. 쉼표가 든 값은 큰따옴표로 감싸세요.')
    return rows


def edit_sheet(path, decisions):
    rows = read_sheet(path)
    for row in rows:
        if row['id'] in decisions:
            status, reason = decisions[row['id']]
            row.update({'판정': status, '근거 또는 이유': reason, '검토자': ACTOR})
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def csv_round(store, label, decisions, interactive=False, wait=input):
    print(f'\n[{label}] CSV 편집 → 저장 → 반영', flush=True)
    print(f'편집할 파일: {store.sheet}', flush=True)
    print('id, revision, content_sha256은 유지하고 판정·근거 또는 이유·검토자만 수정하세요.')
    for ident, (status, reason) in decisions.items():
        print(f'  {ident}: 판정={status} / 이유={reason}')
    print('위에 없는 행은 그대로 둡니다. 검토자에는 실습자 이름을 입력합니다.')
    before = store.output / f'{label}-before.csv'
    edited = store.output / f'{label}-edited.csv'
    shutil.copy2(store.sheet, before)
    while True:
        if interactive:
            if wait('CSV를 편집·저장한 뒤 Enter를 누르세요 (q: 종료): ').strip().lower() == 'q':
                raise InterruptedError('CSV와 작업 공간을 보존하고 시연을 종료했습니다.')
        else:
            edit_sheet(store.sheet, decisions)
            print('자동 시연: 위 판정 예시를 CSV 파일에 기록했습니다.')
        try:
            rows = read_sheet(store.sheet)
            for row in rows:
                expected = decisions.get(row['id'], ('pending', ''))[0]
                if row['판정'].strip() != expected:
                    raise ValueError(f"{row['id']}: 이 시연 단계에서는 {expected}를 기록하세요.")
            # Preserve exactly what was edited before import rewrites the worksheet.
            shutil.copy2(store.sheet, edited)
            saved = store.import_csv()
            break
        except (ValueError, OSError) as exc:
            if not interactive:
                raise
            print(f'반영하지 못했습니다: {exc}\n같은 CSV를 고쳐 저장한 뒤 다시 진행하세요.', flush=True)
    print(f'CSV 반영 완료: {saved}개 판정 저장', flush=True)
    for row in store.current():
        if row['id'] in decisions:
            print(f"  {row['id']} r{row['revision']}: {row['status']} / {row['reviewer']} / {row['review_reason']}")
    print(f'편집 전: {before}\n편집 후: {edited}\n반영 이력: {store.output / "review_history.json"}')


def run_walkthrough(work, interactive=False, wait=input):
    work = Path(work)
    for name in ['assertions.jsonl', 'error_candidates.json', 'review.csv']:
        shutil.copy2(ROOT / name, work / name)
    shutil.copytree(ROOT / 'raw', work / 'raw')
    store = Store(work)
    store.init()
    print(f'교육용 CSV 검토 실습 폴더: {work}', flush=True)
    original = json.loads(next(row for row in store.current() if row['id'] == 'F03')['payload'])
    store.revise('F03', 1, ACTOR, '방향 오류를 검토하기 위한 교육용 사례',
                 dict(original, subject='ledger', object='pay'))
    print('F03 r2에 ledger → pay라는 방향 오류를 넣었습니다. raw/ARCH-01_v1.md §2와 비교하세요.')
    csv_round(store, '01-reject', {
        'F03': ('rejected', 'ARCH-01 v1 §2의 호출은 pay → ledger이므로 반대 방향 반려')
    }, interactive, wait)
    shutil.copy2(store.sheet, work / 'stale-review.csv')
    print('\n[후보 수정] F03의 subject와 object를 원문의 pay → ledger로 교정합니다.')
    store.revise('F03', 2, ACTOR, '원문과 일치하도록 pay → ledger로 교정', original)
    print('F03 r3: pending. review.csv가 새 버전으로 갱신됐습니다. 편집기에서 파일을 다시 여세요.')
    try:
        store.import_csv(work / 'stale-review.csv')
    except ValueError as exc:
        print('이전 CSV 거부 확인:', exc)
    else:
        raise AssertionError('이전 판정이 새 후보에 적용됨')
    decisions = {}
    with (ROOT / 'review.example.csv').open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            decisions[row['id']] = (row['판정'], row['근거 또는 이유'])
    decisions['F03'] = ('approved', 'ARCH-01 v1 §2의 인용과 수정된 pay → ledger 방향을 다시 확인')
    csv_round(store, '02-rereview', decisions, interactive, wait)
    counts = store.export(True)
    approved = verify_export_file(work / 'approved.jsonl')
    assert len(approved) == 3 and next(row for row in approved if row['assertion_id'] == 'F03')['candidate_revision'] == 3
    assert [row['status'] for row in store.history('F03')] == [None, 'rejected', 'approved']
    print('\n[결과 확인] 승인 3개 / 보류 1개 / 반려 5개')
    print('approved.jsonl: F03 r3 승인 / rejected.json·held.json: 최신 판정')
    print('review_history.json: F03 r2 반려 이유와 r3 수정·승인 이력')
    print(f'결과 폴더: {work}\n원래 part03/review.csv와 검토 DB는 변경하지 않았습니다.')
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--interactive', action='store_true', help='CSV를 직접 편집·저장할 때까지 기다립니다.')
    args = parser.parse_args()
    runs = ROOT / 'runs'
    runs.mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='review-walkthrough-' + datetime.now().strftime('%Y%m%d-%H%M%S-'), dir=runs))
    try:
        run_walkthrough(work, args.interactive)
    except (EOFError, KeyboardInterrupt, InterruptedError) as exc:
        parser.exit(1, f'실습 중단: {exc}\n작업 파일: {work}\n')
    except (ValueError, OSError) as exc:
        parser.exit(1, f'실습 오류: {exc}\n작업 파일: {work}\n')


if __name__ == '__main__':
    main()
