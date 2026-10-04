"""Local Markdown corpus, section-level retrieval, immutable source provenance."""
import hashlib
import json
import math
from pathlib import Path
import re

STATUSES={'승인 완료':'approved','검토 중':'draft','리뷰 완료':'reviewed','검토 착수 승인':'analysis_approved'}

class Corpus:
    def __init__(self, root):
        self.root=Path(root).resolve()
        self.docs={}
        for kind in ('raw','wiki'):
            for path in sorted((self.root/kind).rglob('*.md')):
                text=path.read_text(encoding='utf-8')
                if kind=='raw':
                    m=re.search(r'^문서 번호: (\S+) (v\d+)',text,re.M)
                    if not m:continue
                    ident=f'{m[1]}:{m[2]}'
                    state=re.search(r'^상태: (.+)$',text,re.M)[1].strip()
                    status=STATUSES.get(state,state)
                else:
                    ident='wiki:'+path.relative_to(self.root/'wiki').as_posix()
                    status='draft; 사람 검토 대기'
                headings=list(re.finditer(r'^## (.+)$',text,re.M))
                sections={}
                for i,h in enumerate(headings):
                    match=re.match(r'(\d+)\.',h[1])
                    key='§'+match[1] if kind=='raw' and match else str(i+1)
                    sections[key]={'heading':h[1], 'text':text[h.end():headings[i+1].start() if i+1<len(headings) else len(text)].strip()}
                if not sections:sections={'1':{'heading':'본문','text':text}}
                self.docs[ident]={'doc_id':ident,'kind':kind,'status':status,'title':text.splitlines()[0].lstrip('# '),
                  'path':path.relative_to(self.root).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                  'text':text,'sections':sections}
        self.aliases=json.loads((self.root/'ontology/aliases.json').read_text())

    def catalog(self):
        return [{k:v for k,v in d.items() if k in ('doc_id','kind','title','status')} |
                {'sections':{k:v['heading'] for k,v in d['sections'].items()}} for d in self.docs.values()]

    def read(self, doc_id, section=None):
        if doc_id not in self.docs:raise ValueError('알 수 없는 doc_id. catalog의 ID를 사용하세요.')
        d=self.docs[doc_id]
        if section and section not in d['sections']:raise ValueError('알 수 없는 절. catalog의 section을 사용하세요.')
        keys=[section] if section else list(d['sections'])
        return [dict(kind=d['kind'],doc_id=doc_id,title=d['title'],status=d['status'],path=d['path'],
                     sha256=d['sha256'],section=k,heading=d['sections'][k]['heading'],quote=d['sections'][k]['text']) for k in keys]

    def search(self, query, kind='all', limit=5):
        if kind not in {'all','wiki','raw'}:raise ValueError('kind: all/wiki/raw')
        if not isinstance(query,str) or not 1<=len(query)<=300:raise ValueError('검색어는 1~300자입니다.')
        if type(limit)!=int or not 1<=limit<=8:raise ValueError('limit은 1~8입니다.')
        terms=set(re.findall(r'[\w-]+',query.lower()))
        for a in self.aliases:
            if a['alias'].lower() in query.lower():terms.add(a['canonical_id'])
        hits=[]
        for d in self.docs.values():
            if kind!='all' and kind!=d['kind']:continue
            for section,body in d['sections'].items():
                content=(d['title']+' '+body['heading']+' '+body['text']).lower()
                score=sum(1+math.log1p(content.count(t)) for t in terms if t in content)
                if score: hits.append({'doc_id':d['doc_id'],'section':section,'title':d['title'],'heading':body['heading'],
                    'kind':d['kind'],'status':d['status'],'score':round(score,3),'excerpt':body['text'][:350]})
        hits.sort(key=lambda h:(-h['score'],h['doc_id'],h['section']))
        return {'status':'success' if hits else 'empty','hits':hits[:limit],
                'method':'문서·절 키워드 검색. LLM이 재검색어와 읽을 절을 선택합니다. 인용은 read_document로 확보하세요.'}
