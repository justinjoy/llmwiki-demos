"""Commit revision-bound human review and export only current approved candidates."""
import argparse
import csv
import sqlite3
from review_workflow import ROOT,Store,FIELDS


def export(overwrite=False,example=False):
    store=Store(ROOT,example)
    if example:
        if not store.db.exists():store.init()
        store.sync('교육용 예시 실행기(실제 검토 아님)','최신 추출 후보로 강사 시연')
        with (ROOT/'review.example.csv').open(encoding='utf-8-sig',newline='') as f:examples=list(csv.DictReader(f))
        current={r['id']:r for r in store.current()}
        reviews=[]
        for r in examples:
            candidate=current[r['id']]
            reviews.append(dict(zip(FIELDS,[r['id'],str(candidate['revision']),candidate['content_sha'],r['판정'],r['근거 또는 이유'],r['검토자']])))
        store.apply(reviews)
    else:
        # Legacy four-column sheets cannot prove which content the reviewer saw.
        store.import_csv()
    counts=store.export(overwrite)
    print(f"승인 {counts['approved']} / 보류 {counts['held']} / 반려 {counts['rejected']}")
    print('후보별 전체 이력:',store.output/'review_history.json')
    if example:print('교육용 판정 예시입니다. 학습자의 실제 승인 기록이 아닙니다.')
    if not counts['approved']:print('승인된 관계가 없어 다음 교시 입력은 아직 준비되지 않았습니다.')
    return counts

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--overwrite',action='store_true');p.add_argument('--example',action='store_true')
    a=p.parse_args()
    try:export(a.overwrite,a.example)
    except (ValueError,OSError,KeyError,sqlite3.Error) as exc:p.exit(1,str(exc)+'\n')
