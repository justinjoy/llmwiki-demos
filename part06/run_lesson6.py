"""6교시: 실제 S1 조회 → 원문 근거 묶음 → 과잉 해석 비교 → 검색 기록."""
from pathlib import Path
import csv
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'shared'))
from lab import llm_parser,llm,snapshot,engine,save,check_evidence
ROOT=Path(__file__).resolve().parent
TASKS={'evidence':('prompt.txt','evidence_bundle.json',[]),'compare':('prompts/compare.txt','comparison.csv',['evidence_bundle.json']),'plan':('prompts/plan.txt','search_plan.md',['evidence_bundle.json','comparison.csv'])}

def main():
    p=llm_parser(__doc__,TASKS);a=p.parse_args()
    tasks=list(TASKS) if a.task=='all' else [a.task]
    if not a.overwrite and not a.dry_run and any((ROOT/TASKS[t][1]).exists() for t in tasks): p.error('기존 결과가 있습니다. --overwrite로 백업 후 실행하세요.')
    if not a.dry_run and ('evidence' in tasks or not (ROOT/'input.json').exists()):
        result=engine(ROOT,snapshot('S1'),(ROOT/'model.dl').read_text(),(ROOT/'rules.dl').read_text(),output='S1_result.json')
        save(ROOT,'input.json',{'snapshot_id':'S1','candidates':[r[0] for r in result['relations']['candidate']],
              'initial_doc_ids':sorted({r[1] for r in result['relations']['candidate_doc']}),'rule_id':'candidate-v1','paths':result['paths']})
    for task in tasks:
        prompt,out,extra=TASKS[task]
        if extra and not a.dry_run:check_evidence(ROOT/'evidence_bundle.json',ROOT/'raw')
        llm(ROOT,a,prompt,[ROOT/'input.json',*sorted((ROOT/'raw').glob('*.md')),*[ROOT/n for n in extra]],out)
        if a.dry_run:continue
        if task=='evidence':check_evidence(ROOT/out,ROOT/'raw')
        if task=='compare':
            with (ROOT/out).open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
            if {r.get('후보') for r in rows}!={'A','B','C'} or any(None in r for r in rows):raise ValueError('A/B/C 비교 CSV 형식을 확인하세요.')
    print('6교시 완료. 생성 내용의 의미와 현재 적용 여부는 원문과 대조하세요.')

if __name__=='__main__':
    try:main()
    except (OSError,ValueError,RuntimeError) as e:raise SystemExit(str(e))
