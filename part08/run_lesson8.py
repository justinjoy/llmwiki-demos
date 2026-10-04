"""8교시: 실제 S1b 결과와 문맥 근거로 답변·주장 검토·위키 초안·변경 기록 생성."""
from datetime import datetime
import csv
import difflib
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'shared'))
from lab import llm_parser,llm,snapshot,engine,save,read_json,check_evidence,documents
from check_links import check
ROOT=Path(__file__).resolve().parent
TASKS={'answer':('prompt.txt','final_answer.md',[]),
       'claims':('prompts/claims.txt','claim_review.csv',['final_answer.md']),
       'wiki':('prompts/wiki.txt','wiki/analysis/ledger-impact-S1b.md',['final_answer.md','claim_review.csv']),
       'review':('prompts/review.txt','change_review.md',['final_answer.md','wiki/analysis/ledger-impact-S1b.md','change.diff','wiki/log.md'])}

def prepare():
    data=snapshot('S1b')
    previous=ROOT.parent/'part07/S1b_input.json'
    if previous.exists():
        from lab import check_assertions
        data=read_json(previous);check_assertions(data['assertions'],'S1b')
    save(ROOT,'S1b_input.json',data)
    result=engine(ROOT,data,(ROOT/'model.dl').read_text(),(ROOT/'rules.dl').read_text(),output='S1b_result.json')
    evidence_path=ROOT.parent/'part06/evidence_bundle.json'
    if not evidence_path.exists():raise ValueError('먼저 part06/run_lesson6.py --task evidence를 실행하세요.')
    bundle=check_evidence(evidence_path,ROOT/'raw')
    bundle.update(snapshot_id='S1b',candidates=[r[0] for r in result['relations']['candidate']],expanded_doc_ids=['OPS-04:v1','RUN-02:v1'],
                  expansion_reason='ADR-07 §3 → OPS-04; ARCH-01 §4 → RUN-02',mode='6교시 실제 LLM 결과 + RUN-02 원문 절; 교육 시연 초안, 사람 검토 대기')
    docs=documents(ROOT/'raw')
    for section in ['§1','§2']:
        bundle['items'].append({'service':'notify','source_id':'RUN-02','version':'v1','section':section,
         'quote':docs['RUN-02:v1']['sections'][section],'evidence_kind':'알림 호출과 격리 조건','explanation':'원문 절 전문. 현재 알림 지연 발생 여부는 별도 관측 필요.','interpretation':None})
    save(ROOT,'evidence_bundle.json',bundle);check_evidence(ROOT/'evidence_bundle.json',ROOT/'raw','S1b')

def finish_wiki(before):
    for rel,label,target in [('wiki/services/pay.md','ledger 영향 분석','../analysis/ledger-impact-S1b.md'),
                             ('wiki/services/order.md','ledger 영향 분석','../analysis/ledger-impact-S1b.md'),
                             ('wiki/index.md','ledger 영향 분석','analysis/ledger-impact-S1b.md')]:
        text=(ROOT/rel).read_text()
        text=text.replace('TODO: 분석 페이지 작성 후 연결합니다.','분석 페이지는 S1b 기준의 검토 대기 초안입니다.')
        if target not in text:save(ROOT,rel,text+f'\n- [{label}]({target}) — S1b / 검토 대기\n')
        elif text != (ROOT/rel).read_text():save(ROOT,rel,text)
    stamp=datetime.now().astimezone().isoformat(timespec='seconds')
    log=(ROOT/'wiki/log.md').read_text()
    save(ROOT,'wiki/log.md',log+f'\n## {stamp} · S1b 분석 초안\n\n생성: LLM CLI와 실행 스크립트. 상태: 사람 검토 대기. candidate-v1 결과·원문 근거로 분석 페이지와 서비스·index 링크를 갱신했습니다. 실제 검토자·검토 일자는 사람이 확인 후 기록합니다. 원문 파일은 보존했습니다.\n')
    diff=[]
    for path in sorted((ROOT/'wiki').rglob('*.md')):
        rel=path.relative_to(ROOT).as_posix()
        diff.extend(difflib.unified_diff(before.get(rel,'').splitlines(True),path.read_text().splitlines(True),fromfile='before/'+rel,tofile='after/'+rel))
    save(ROOT,'change.diff',''.join(diff))
    errors=check(ROOT/'wiki')
    if errors:raise ValueError('위키 링크 검사 실패:\n'+'\n'.join(errors))

def main():
    p=llm_parser(__doc__,TASKS);a=p.parse_args()
    tasks=list(TASKS) if a.task=='all' else [a.task]
    if not a.overwrite and not a.dry_run and any((ROOT/TASKS[t][1]).exists() for t in tasks):p.error('--overwrite로 기존 결과 백업 후 실행하세요.')
    if not a.dry_run:
        if 'answer' in tasks:prepare()
        check_evidence(ROOT/'evidence_bundle.json',ROOT/'raw','S1b')
    base=[ROOT/'S1b_result.json',ROOT/'evidence_bundle.json',*sorted((ROOT/'raw').glob('*.md'))]
    for task in tasks:
        prompt,out,extra=TASKS[task]
        before={p.relative_to(ROOT).as_posix():p.read_text() for p in (ROOT/'wiki').rglob('*.md')} if task=='wiki' else {}
        llm(ROOT,a,prompt,[*base,*[ROOT/n for n in extra]],out)
        if a.dry_run:continue
        if task=='claims':
            with (ROOT/out).open(encoding='utf-8-sig',newline='') as f:
                reader=csv.DictReader(f);rows=list(reader)
                if reader.fieldnames!=['주장','유형','근거','판정'] or not rows or any(None in r or None in r.values() for r in rows):raise ValueError('주장 검토 CSV 형식을 확인하세요.')
        if task=='wiki':finish_wiki(before)
    print('8교시 완료. 답변·주장표·위키 초안·실제 변경 diff를 저장했습니다.')

if __name__=='__main__':
    try:main()
    except (OSError,ValueError,RuntimeError) as e:raise SystemExit(str(e))
