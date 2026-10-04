"""Approved snapshot facts → real PyreWire relations and assertion paths."""
from collections import deque
import json
from .engine import evaluate

SERVICES={'shop','order','pay','ledger','notify'}
MODEL='''.decl depends_on(src:symbol,dst:symbol)
.decl about(doc:symbol,svc:symbol)
.decl direct(src:symbol,dst:symbol)
.decl reach(src:symbol,dst:symbol)
.decl doc_link(doc:symbol,svc:symbol)
direct(X,Y):-depends_on(X,Y).
reach(X,Y):-depends_on(X,Y).
reach(X,Z):-depends_on(X,Y),reach(Y,Z).
doc_link(D,S):-about(D,S).
'''

class Graph:
    def __init__(self, corpus):
        self.corpus=corpus
        self.snapshots={}
        for name in ('S1','S1b','S2','S3'):
            d=json.loads((corpus.root/'snapshots'/f'{name}.json').read_text())
            if d['snapshot_id']!=name:raise ValueError('스냅샷 ID 불일치')
            seen=set()
            for f in d['assertions']:
                if f['assertion_id'] in seen:raise ValueError('중복 사실 ID')
                seen.add(f['assertion_id'])
                if f['predicate']!='depends_on' or f['subject_type']!='Service' or f['object_type']!='Service':raise ValueError('Service 관계만 허용')
                if f['subject'] not in SERVICES or f['object'] not in SERVICES:raise ValueError('서비스 ID 오류')
                if f['review_status']!='approved' or not f['reviewer'].strip() or f['snapshot_id']!=name:raise ValueError('미승인·스냅샷 혼용 사실')
                doc=corpus.docs[f"{f['source_id']}:{f['version']}"]
                if not f['quote'] or f['quote'] not in doc['sections'][f['section']]['text']:raise ValueError('원문과 다른 인용')
                if f['document_status']!=doc['status']:raise ValueError('문서 상태 불일치')
                if doc['status']!='approved' and not (d['snapshot_kind']=='scenario' and f.get('fact_kind')=='scenario' and doc['status']=='analysis_approved'):raise ValueError('검토안의 운영 사실 적재 금지')
            self.snapshots[name]=d

    @staticmethod
    def path(facts, source, target):
        q=deque([(source,[],[source])]);seen={source}
        while q:
            node,ids,nodes=q.popleft()
            if node==target:return {'services':nodes,'assertion_ids':ids}
            for f in facts:
                if f['subject']==node and f['object'] not in seen:
                    seen.add(f['object']);q.append((f['object'],ids+[f['assertion_id']],nodes+[f['object']]))
        return None

    def query(self, action, service, snapshot='S1b', target=None):
        if snapshot not in self.snapshots:raise ValueError('snapshot: S1/S1b/S2/S3')
        if service not in SERVICES or (target is not None and target not in SERVICES):raise ValueError('Service ID를 사용하세요. ledger-db/ledger-batch는 별도 타입입니다.')
        if action not in {'upstream','downstream','direct','path','documents'}:raise ValueError('지원하지 않는 그래프 질의')
        if action=='path' and target is None:raise ValueError('path는 target이 필요합니다.')
        d=self.snapshots[snapshot];lit=lambda v:json.dumps(v,ensure_ascii=False)
        facts='\n'.join(f'depends_on({lit(f["subject"])},{lit(f["object"])}).' for f in d['assertions'])
        facts+='\n'+'\n'.join(f'about({lit(doc)},{lit(svc)}).' for doc,svc in d['about'])
        relations=evaluate(MODEL,facts)['relations']
        reach=relations.get('reach',[])
        if action=='upstream':rows=[r for r in reach if r[1]==service and r[0]!=service]
        elif action=='downstream':rows=[r for r in reach if r[0]==service and r[1]!=service]
        elif action=='direct':rows=[r for r in relations.get('direct',[]) if r[0]==service]
        elif action=='path':rows=[r for r in reach if r==[service,target]]
        else:rows=[r for r in relations.get('doc_link',[]) if r[1]==service]
        paths=[self.path(d['assertions'],a,b) for a,b in rows] if action!='documents' else []
        ids={ident for path in paths if path for ident in path['assertion_ids']}
        return {'kind':'graph','status':'success' if rows else 'empty','engine':'pyrewire','engine_version':'1.1.2',
          'snapshot':snapshot,'snapshot_kind':d['snapshot_kind'],'action':action,'service':service,'target':target,
          'rows':rows,'paths':paths,'facts':[f for f in d['assertions'] if f['assertion_id'] in ids],
          'rule_id':'reach-v1','rules':MODEL,
          'scope':'교육용 승인 예시 / S2·S3는 설계 가정. 경로는 점검 후보이며 실제 장애 확정이 아닙니다. about은 초기 3개 링크로 제한됩니다.'}
