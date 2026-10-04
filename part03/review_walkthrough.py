"""Exercise reject → correction → re-review in an isolated, clearly labeled example."""
from datetime import datetime
import json
from pathlib import Path
import shutil
import tempfile
from review_workflow import ROOT,Store,verify_export_file

if __name__=='__main__':
    runs=ROOT/'runs';runs.mkdir(exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix='review-walkthrough-'+datetime.now().strftime('%Y%m%d-%H%M%S-'),dir=runs))
    for name in ['assertions.jsonl','error_candidates.json','review.csv']:shutil.copy2(ROOT/name,work/name)
    shutil.copytree(ROOT/'raw',work/'raw')
    store=Store(work);store.init();actor='교육용 시연(실제 검토 아님)'
    original=json.loads(next(r for r in store.current() if r['id']=='F03')['payload'])
    store.revise('F03',1,actor,'방향 오류를 검토하기 위한 교육용 사례',dict(original,subject='ledger',object='pay'))
    store.decide('F03',2,'rejected',actor,'ARCH-01 v1 §2에서 직접 호출은 pay → ledger이므로 반대 방향 반려')
    shutil.copy2(store.sheet,work/'stale-review.csv')
    store.revise('F03',2,actor,'원문과 일치하도록 pay → ledger로 교정',original)
    try:store.import_csv(work/'stale-review.csv')
    except ValueError as exc:print('이전 CSV 거부 확인:',exc)
    else:raise AssertionError('이전 판정이 새 후보에 적용됨')
    store.decide('F03',3,'approved',actor,'수정된 방향과 ARCH-01 v1 §2 인용을 다시 확인')
    for r in store.current():
        if r['status']=='pending':
            status='approved' if r['kind']=='assertion' else 'held' if r['id']=='E04' else 'rejected'
            store.decide(r['id'],r['revision'],status,actor,'최종 교육자료의 판정 예시. 실제 사람 검토와 구분')
    counts=store.export(True);approved=verify_export_file(work/'approved.jsonl')
    assert len(approved)==3 and next(r for r in approved if r['assertion_id']=='F03')['candidate_revision']==3
    history=store.history('F03');assert [r['status'] for r in history]==[None,'rejected','approved']
    print(json.dumps({'status':'success','counts':counts,'candidate':'F03','versions':3,'history':str(work/'review_history.json')},ensure_ascii=False,indent=2))
    print('학습자의 review.csv와 검토 DB는 변경하지 않았습니다.')
