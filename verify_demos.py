"""Verify demos with PyreWire >=1.1.2; never calls an LLM."""
from packaging.version import Version
import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'shared'))
from lab import read_json,documents,check_quote,check_assertions,check_evidence,snapshot,facts_text,evaluate,trace
from check_links import check


def main():
    passed=[]
    from importlib.metadata import version
    installed_version=version('pyrewire')
    assert Version(installed_version) >= Version('1.1.2')
    def ok(name,condition):
        if not condition:raise AssertionError(name)
        passed.append(name)
    for part in range(3,9):
        folder=ROOT/f'part{part:02}'
        for p in folder.glob('raw/*.md'):
            ok(f'{part}교시 원문 보존 {p.name}',p.read_bytes()==(ROOT/'shared/common/raw'/p.name).read_bytes())
        errors=check(folder)
        ok(f'{part}교시 상대 링크: '+str(errors),not errors)
        for p in folder.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
    ok('Python 구문 검사',True)
    # Import the self-contained lesson 3 runner without relying on the working directory.
    sys.path.insert(0,str(ROOT/'part03'))
    spec=importlib.util.spec_from_file_location('lesson3_checks',ROOT/'part03/run_lesson3.py')
    lesson3=importlib.util.module_from_spec(spec);spec.loader.exec_module(lesson3)
    for task in lesson3.TASKS:lesson3.validate_output(task)
    ok('3교시 실제 LLM 출력 구조·인용',True)
    approved=[json.loads(l) for l in (ROOT/'part03/example_output/approved.jsonl').read_text().splitlines()]
    check_assertions(approved)
    ok('3교시 예시 내보내기 3/1/5',len(approved)==3 and len(read_json(ROOT/'part03/example_output/held.json'))==1 and len(read_json(ROOT/'part03/example_output/rejected.json'))==5)
    ok('3교시 학습자 자동 승인 없음',(ROOT/'part03/approved.jsonl').read_text()=='')
    model=(ROOT/'part04/model.dl').read_text();rules=(ROOT/'part05/rules.dl').read_text()
    counts={'S1':(3,6,3,3),'S2':(4,6,3,3),'S3':(3,5,2,1),'S1b':(4,9,4,3)}
    for name,expected in counts.items():
        data=snapshot(name);rel=evaluate(model,facts_text(data),rules)['relations']
        got=tuple(len(rel.get(key,[])) for key in ['direct','reach','candidate','candidate_doc'])
        ok(f'실제 Wirelog {name}: {got}',got==expected)
        path=ROOT/('part08/S1b_result.json' if name=='S1b' else f'part05/{name}_result.json')
        ok(f'{name} 저장 결과와 재계산 일치',read_json(path)['relations']==rel)
    p4=ROOT/'part04'
    ok('4교시 기본 질의',read_json(p4/'result.json')['relations']['pay_doc']==[['ARCH-01:v1'],['INC-03:v1']])
    extended=read_json(p4/'extended_result.json')['relations']
    ok('4교시 추가 질의',extended['order_doc']==[['ADR-07:v1']] and extended['shop_dep']==[['order']])
    ok('4교시 열 수 오류 검출',read_json(p4/'invalid_result.json')['status']=='expected_error')
    ok('4교시 방향 오류는 문법상 성공',read_json(p4/'direction_result.json')['status']=='success' and ['pay','order'] in read_json(p4/'direction_result.json')['relations']['direct'])
    delta=(ROOT/'part05/delta_actual.txt').read_text().splitlines()
    ok('PyreWire 동일 세션 +2/0/-2 실제 출력',sum(s.startswith('+ mutual') for s in delta)==2 and sum(s.startswith('- mutual') for s in delta)==2 and read_json(ROOT/'part05/delta_run.json')['status']=='success' and read_json(ROOT/'part05/delta_run.json')['steps'][1]['events']==[])
    for n,sid in [(6,'S1'),(8,'S1b')]:
        check_evidence(ROOT/f'part{n:02}/evidence_bundle.json',ROOT/f'part{n:02}/raw',sid)
        ok(f'{n}교시 근거·범위·인용 검사',True)
    for sid in ['S1','S1b']:
        log=read_json(ROOT/f'part07/{sid}_log.json');calls=log['calls']
        ok(f'7교시 {sid} 6회 예산',len(calls)==log['call_budget']==6)
        ok(f'7교시 {sid} 중복 호출 없음',len({json.dumps([c['tool'],c['input']],sort_keys=True) for c in calls})==6)
        ok(f'7교시 {sid} 읽기 도구만 사용',all(c['tool'] in {'find_candidates','find_documents','search_context','trace_path'} for c in calls))
        ok(f'7교시 {sid} 실제 엔진 결과',log['engine_result']['engine']=='pyrewire' and Version(log['engine_result']['engine_version'])>=Version('1.1.2') and log['engine_result']['status']=='success')
        start='notify' if sid=='S1b' else 'shop'
        ok(f'7교시 {sid} 사실 ID 경로',calls[-1]['output']['assertion_ids']==trace(snapshot(sid),start)['assertion_ids'])
        ok(f'7교시 {sid} 원문 링크로 확장',calls[3]['input']['doc_ids']==['OPS-04:v1'] and calls[4]['input']['doc_ids']==['RUN-02:v1'])
    ok('F04는 미검토 후보',read_json(ROOT/'part07/F04_pending.json')['review_status']=='pending')
    for field,value in [('review_status','pending'),('quote','존재하지 않는 인용'),('snapshot_id','S2')]:
        rows=copy.deepcopy(approved);rows[0][field]=value
        try:check_assertions(rows)
        except ValueError:pass
        else:raise AssertionError('잘못된 입력을 허용함: '+field)
    ok('미승인·허위 인용·스냅샷 혼용 차단',True)
    empty=evaluate(model,'')['relations']
    ok('빈 결과와 실행 오류 구분',not empty)
    try:evaluate('this is invalid datalog','')
    except (ValueError,RuntimeError):pass
    else:raise AssertionError('잘못된 Datalog가 성공 처리됨')
    ok('실제 엔진 오류 전파',True)
    symbols=evaluate('.decl edge(a:symbol,b:symbol) .decl direct(a:symbol,b:symbol)\ndirect(A,B):-edge(A,B).',
                     '// ignored \"comment\"\nedge("서비스 A", "서비스 B").')['relations']
    ok('PyreWire 문자열 이름 복원',symbols['direct']==[['서비스 A','서비스 B']])
    from query import require_pyrewire
    import query
    original_version=query.version
    try:
        query.version=lambda _: '0.1.0'
        try:require_pyrewire()
        except RuntimeError:pass
        else:raise AssertionError('0.1.0을 허용함')
    finally:query.version=original_version
    ok('구버전 실행 차단',True)
    spec=importlib.util.spec_from_file_location('delta_test',ROOT/'part05/session_delta.py')
    delta_test=importlib.util.module_from_spec(spec);spec.loader.exec_module(delta_test)
    ok('동일 EasySession 증분 재실행',delta_test.run_delta()['status']=='success')

    successes=set()
    for n in [3,6,7,8]:
        for p in (ROOT/f'part{n:02}/runs').glob('*/run.json'):
            row=read_json(p)
            if row.get('status')=='success' and row.get('cli')=='agy':successes.add((n,Path(row['output']).name))
    ok('LLM 13개 단계의 실제 성공 기록',len(successes)>=13)
    answer=(ROOT/'part08/final_answer.md').read_text();wiki=(ROOT/'part08/wiki/analysis/ledger-impact-S1b.md').read_text()
    ok('최종 답변의 기준·조건·미확인',all(s in answer for s in ['S1b','candidate-v1','notify','25분','42분','5분','미확인']))
    ok('위키는 사람 검토 대기',all(s in wiki for s in ['검토 대기','F04','F02','F03']))
    ok('실제 위키 변경 diff',(ROOT/'part08/change.diff').read_text().startswith('--- before/wiki/'))
    report={'status':'success','checks':len(passed),'pyrewire_version':installed_version,'llm_completed_outputs':len(successes),'passed':passed}
    (ROOT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(f'PASS: {len(passed)} checks; PyreWire {installed_version} 4 snapshots; LLM {len(successes)} completed outputs; sources, quotes, links, review boundaries.')

if __name__=='__main__':main()
