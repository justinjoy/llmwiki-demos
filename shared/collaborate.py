"""Fixed manual plan: real Wirelog + source reading, no LLM API calls."""
import argparse,json
from collections import deque
from pathlib import Path
from query import evaluate
ROOT=Path(__file__).resolve().parent

def run(snapshot, data=None):
    if snapshot not in {'S1','S1b'}:raise ValueError('7교시 기준은 S1 또는 S1b입니다.')
    data=data or json.loads((ROOT/f'common/snapshots/{snapshot}.json').read_text(encoding='utf-8'))
    from lab import check_assertions, facts_text
    check_assertions(data['assertions'], snapshot)
    docs=json.loads((ROOT/'common/documents.json').read_text(encoding='utf-8'))
    result=evaluate((ROOT/'common/model.dl').read_text(),facts_text(data),(ROOT/'common/rules.dl').read_text())
    rel=result['relations'];log=[]
    def record(tool,args,result):
        if len(log)>=6:raise RuntimeError('호출 예산 6회 초과')
        if any(c['tool']==tool and c['input']==args for c in log):raise RuntimeError('동일 호출 반복')
        log.append(dict(tool=tool,input=args,output=result))
    def read(doc_ids,reason):
        passages=[]
        for d in doc_ids:
            if d not in docs:raise ValueError('알 수 없는 문서: '+d)
            for section,quote in docs[d]['sections'].items():
                passages.append(dict(doc_id=d,section=section,quote=quote,status=docs[d]['status'],scope=docs[d]['scope']))
        record('search_context',dict(doc_ids=doc_ids,question="설계 이유·조치 조건·타임라인·알림 영향",reason=reason),dict(status='success' if passages else 'empty',passages=passages,method='선택한 원문의 전체 절 읽기; LLM 의미 검색 아님'))
        return passages
    services=[r[0] for r in rel.get('candidate',[])]
    record('find_candidates',dict(target='ledger',snapshot_id=snapshot),dict(status='success' if services else 'empty',services=services,snapshot_id=snapshot,rule_id='candidate-v1'))
    doc_ids=sorted({r[1] for r in rel.get('candidate_doc',[])})
    record('find_documents',dict(service_ids=services,snapshot_id=snapshot),dict(status='success' if doc_ids else 'empty',doc_ids=doc_ids,scope='첫 적재 about 링크만 사용'))
    initial=read(doc_ids,'구조 질의의 초기 문서')
    for next_doc,source,section in [('OPS-04:v1','ADR-07:v1','§3'),('RUN-02:v1','ARCH-01:v1','§4')]:
        supported=any(p['doc_id']==source and p['section']==section and next_doc.split(':')[0] in p['quote'] for p in initial)
        if not supported:raise ValueError('원문에서 후속 참조를 찾을 수 없음: '+next_doc)
        read([next_doc],f'{source} {section}의 명시적 참조로 범위 확장')
    start='notify' if snapshot=='S1b' else 'shop'
    queue=deque([(start,[])]);seen={start};path=[]
    while queue:
        node,ids=queue.popleft()
        if node=='ledger':path=ids;break
        for fact in data['assertions']:
            if fact['subject']==node and fact['object'] not in seen:
                seen.add(fact['object']);queue.append((fact['object'],ids+[fact['assertion_id']]))
    record('trace_path',dict(service=start,target='ledger',snapshot_id=snapshot),dict(status='success' if path else 'empty',assertion_ids=path,method='승인 직접 사실의 별도 경로 계층'))
    return dict(status='success',mode='manual_plan_real_pyrewire_no_llm_api',snapshot_id=snapshot,call_budget=6,calls=log,engine_result=result,new_relation_status='pending; 사람 검토 후 제공 S1b 체크포인트로 별도 재실행' if snapshot=='S1' else 'S1b는 검토 완료 예시 입력',stop_reason='원문 확장과 근거 경로 확인 완료; 현재 운영 판단은 추가 관측 필요',gaps=['현재 오류·큐 적체 지표','현재 PG 승인·원장 불일치와 영향 범위','건별 실행 승인','향후 복구 예상 시각'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--snapshot',choices=['S1','S1b'],required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:result=run(a.snapshot)
    except (OSError,ValueError,RuntimeError) as e:result=dict(status='error',snapshot_id=a.snapshot,message=str(e))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(a.output);raise SystemExit(0 if result['status']=='success' else 1)
if __name__=='__main__':main()
