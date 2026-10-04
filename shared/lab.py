"""Shared file, provenance and CLI helpers for the final-slide exercises."""
import argparse
from collections import deque
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from query import evaluate
import run_prompt

HERE = Path(__file__).resolve().parent
DEMOS = HERE.parent


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(root, name, value):
    """Preserve previous outputs and replace individual files atomically."""
    path = Path(root) / name
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding='utf-8') == text:
        return path
    if path.exists():
        log = Path(root) / 'runs' / datetime.now().strftime('files-%Y%m%d-%H%M%S-%f')
        log.mkdir(parents=True)
        shutil.copy2(path, log / ('previous-' + path.name))
        (log/'change.json').write_text(json.dumps({'output':str(path),'kind':'file_update'},ensure_ascii=False))
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.write-')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f: f.write(text)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    return path


def documents(raw=None):
    result = {}
    statuses = {'승인 완료':'approved','검토 중':'draft','리뷰 완료':'reviewed','검토 완료':'reviewed','분석 승인':'analysis_approved','검토 착수 승인':'analysis_approved'}
    for path in (Path(raw) if raw else HERE/'common/raw').glob('*.md'):
        text = path.read_text(encoding='utf-8')
        match = re.search(r'^문서 번호: (\S+) (v\d+)',text,re.M)
        if not match: continue
        state = re.search(r'^상태: (.+)$',text,re.M).group(1).strip()
        headers = list(re.finditer(r'^## (\d+)\. [^\n]+\n',text,re.M))
        sections = {}
        for i,h in enumerate(headers):
            end=headers[i+1].start() if i+1<len(headers) else len(text)
            sections['§'+h.group(1)] = text[h.end():end].strip()
        result[match.group(1)+':'+match.group(2)]={'sections':sections,'status':statuses.get(state,state),'file':str(path)}
    return result


def check_quote(row, docs=None):
    docs = docs or documents()
    for key in ['source_id','version','section','quote']:
        if not isinstance(row.get(key),str) or not row[key].strip():
            raise ValueError('원문 근거 필드가 필요합니다: '+key)
    doc = docs.get(row['source_id']+':'+row['version'])
    if not doc or row['quote'] not in doc['sections'].get(row['section'],''):
        raise ValueError('원문 절에 없는 인용: '+repr(row))
    return doc


def check_assertions(rows, snapshot='S1', allow_scenario=False):
    if not rows: raise ValueError('승인 사실이 비어 있습니다.')
    seen=set()
    for row in rows:
        doc=check_quote(row)
        ident=row.get('assertion_id')
        if not ident or ident in seen: raise ValueError('중복 또는 빈 사실 ID')
        seen.add(ident)
        if row.get('predicate')!='depends_on' or any(row.get(k)!='Service' for k in ['subject_type','object_type']):
            raise ValueError('Service 간 depends_on만 적재합니다.')
        if any(row.get(k) not in {'shop','order','pay','ledger','notify'} for k in ['subject','object']):
            raise ValueError('알 수 없는 서비스 ID')
        if row.get('review_status')!='approved' or not row.get('reviewer','').strip():
            raise ValueError('검토자 기록을 포함한 승인 사실만 적재합니다.')
        if row.get('snapshot_id')!=snapshot: raise ValueError('스냅샷 불일치')
        if row.get('document_status')!=doc['status']: raise ValueError('문서 상태 불일치')
        if doc['status']!='approved' and not (allow_scenario and row.get('fact_kind')=='scenario' and doc['status']=='analysis_approved'):
            raise ValueError('운영 승인 사실과 설계 분석 가정을 구분하세요.')


def snapshot(name):
    data=read_json(HERE/f'common/snapshots/{name}.json')
    check_assertions(data['assertions'],name,data['snapshot_kind']=='scenario')
    return data


def facts_text(data):
    def literal(value): return json.dumps(value,ensure_ascii=False)
    rows=['depends_on('+literal(r['subject'])+', '+literal(r['object'])+').' for r in data['assertions']]
    rows += ['about('+literal(d)+', '+literal(s)+').' for d,s in data['about']]
    return '\n'.join(dict.fromkeys(rows))+'\n'


def trace(data, service, target='ledger'):
    queue=deque([(service,[],[service])]);seen={service}
    while queue:
        node,ids,nodes=queue.popleft()
        if node==target: return {'service':service,'target':target,'assertion_ids':ids,'services':nodes}
        for row in data['assertions']:
            if row['subject']==node and row['object'] not in seen:
                seen.add(row['object']);queue.append((row['object'],ids+[row['assertion_id']],nodes+[row['object']]))
    return {'service':service,'target':target,'assertion_ids':[],'services':[]}


def engine(root, data, model, rules='', output='result.json'):
    source=model+'\n'+facts_text(data)+'\n'+rules
    log=Path(tempfile.mkdtemp(prefix=datetime.now().strftime('engine-%Y%m%d-%H%M%S-'),dir=ensure_runs(root)))
    (log/'input.dl').write_text(source,encoding='utf-8')
    try:
        result=evaluate(model,facts_text(data),rules)
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as exc:
        (log/'run.json').write_text(json.dumps({'status':'error','error':str(exc)},ensure_ascii=False,indent=2))
        raise
    result.update(snapshot_id=data['snapshot_id'],snapshot_kind=data['snapshot_kind'],rule_id=data['rule_id'],
                  input_kind=data.get('input_kind','최종 교육자료의 승인 예시 체크포인트'),
                  source_sha256=hashlib.sha256(source.encode()).hexdigest())
    result['paths']=[trace(data,r[0]) for r in result['relations'].get('candidate',[])]
    (log/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (log/'run.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    save(root,output,result)
    print(f"PyreWire {data['snapshot_id']}: {output}")
    return result


def ensure_runs(root):
    path=Path(root)/'runs';path.mkdir(exist_ok=True);return path


def llm_parser(description,tasks):
    p=argparse.ArgumentParser(description=description)
    p.add_argument('--task',choices=[*tasks,'all'],default='all')
    p.add_argument('--cli',default='agy')
    p.add_argument('--cli-arg',action='append',default=[])
    p.add_argument('--mode',choices=['auto','print','codex'],default='auto')
    p.add_argument('--timeout',type=float,default=600)
    p.add_argument('--overwrite',action='store_true')
    p.add_argument('--dry-run',action='store_true')
    return p


def llm(root,args,prompt,contexts,output):
    params=argparse.Namespace(**vars(args))
    params.prompt=str(root/prompt);params.context=[str(Path(p)) for p in contexts]
    params.output=str(root/output);params.log_dir=str(root/'runs')
    rc=run_prompt.execute(params)
    if rc: raise RuntimeError(f'LLM 실행 실패: {output}, 종료 코드 {rc}')


def check_evidence(path, raw, expected_snapshot='S1'):
    data=read_json(path)
    if data.get('snapshot_id')!=expected_snapshot: raise ValueError('근거 묶음 스냅샷 불일치')
    expected={'shop','order','pay'}|({'notify'} if expected_snapshot=='S1b' else set())
    if set(data.get('candidates',[]))!=expected: raise ValueError('구조 질의의 후보 집합을 유지하세요.')
    if set(data.get('initial_doc_ids',[]))!={'ARCH-01:v1','ADR-07:v1','INC-03:v1'}: raise ValueError('초기 about 범위 불일치')
    expansion={'OPS-04:v1'}|({'RUN-02:v1'} if expected_snapshot=='S1b' else set())
    if set(data.get('expanded_doc_ids',[]))!=expansion: raise ValueError('확장 문서를 별도로 기록하세요.')
    items=data.get('items')
    if not isinstance(items,list) or not items: raise ValueError('근거 항목이 비어 있습니다.')
    docs=documents(raw)
    for row in items:
        check_quote(row,docs)
        if row.get('service') not in expected: raise ValueError('근거 항목의 서비스 ID를 확인하세요.')
    if not isinstance(data.get('gaps'),list) or not data['gaps']: raise ValueError('현재 미확인 사항이 필요합니다.')
    needed={('ADR-07','§1'),('INC-03','§3'),('OPS-04','§1'),('OPS-04','§2')}
    if expected_snapshot=='S1b': needed.add(('RUN-02','§2'))
    if not needed <= {(r['source_id'],r['section']) for r in items}: raise ValueError('필수 설계·관측·정책·알림 근거가 빠졌습니다.')
    return data
