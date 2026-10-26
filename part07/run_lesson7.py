"""7교시: 수동 계획의 실제 읽기 도구 실행, F04 추출, S1b 체크포인트 비교."""
from pathlib import Path
from functools import partial
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'shared'))
from lab import llm_parser,llm,snapshot,save,check_quote,read_json,check_assertions,documents
from collaborate import run
ROOT=Path(__file__).resolve().parent
TASKS=['inspect','extract','compare','decision']

def main():
    p=llm_parser(__doc__,TASKS);p.add_argument('--approved-f04',type=Path)
    a=p.parse_args();tasks=TASKS if a.task=='all' else [a.task]
    if a.dry_run and any(t in tasks for t in ['inspect','compare']):p.error('읽기 도구 단계는 실제 실행합니다. 미리보기는 --task extract 또는 decision에 사용하세요.')
    for task in tasks:
        if task=='inspect':
            result=run('S1',progress=partial(print,flush=True))
            saved=save(ROOT,'S1_log.json',result)
            print(f'[저장 완료] {saved}',flush=True)
        elif task=='extract':
            progress=partial(print,flush=True)
            progress('[extract 시작] 알림 운영 문서에서 직접 API 호출의 주체·대상·근거 절을 찾아 F04 검토 대기 초안으로 추출합니다.')
            llm(ROOT,a,'prompt.txt',[ROOT/'raw/RUN-02_v1.md',ROOT/'raw/GLOSS-01_v1.md'],'F04_pending.json',progress=progress)
            if not a.dry_run:
                progress('[검증 1/3] F04_pending.json을 JSON 객체로 읽습니다.')
                row=read_json(ROOT/'F04_pending.json')
                if not isinstance(row,dict):raise ValueError('F04 추출 결과는 JSON 객체여야 합니다.')
                progress('[검증 2/3] 출처 ID·버전·절·인용문을 확인하고 해당 원문 절에 인용문이 존재하는지 대조합니다.')
                check_quote(row,documents(ROOT/'raw'))
                progress(f"[인용 검증 완료] {row['source_id']} {row['version']} {row['section']}: {row['quote']}")
                progress('[검증 3/3] 생성 결과를 교육용 기대 필드(식별자·관계 방향·검토 상태·검토자·스냅샷·문서 상태)와 대조합니다.')
                for key,value in {'assertion_id':'F04','subject':'notify','object':'order','predicate':'depends_on','review_status':'pending','reviewer':'','snapshot_id':'S1b','document_status':'approved'}.items():
                    if row.get(key)!=value:raise ValueError('F04 추출 필드를 확인하세요: '+key)
                    progress(f'[필드 확인] {key} = {value!r}')
                progress('[extract 완료] F04_pending.json 저장 및 검증 완료. review_status=pending이며 사람의 검토가 필요합니다.')
            else:
                progress('[extract 미리보기 완료] 입력 생성 완료. 추출 결과 검증은 실제 실행 시 수행합니다.')
        elif task=='compare':
            s1=run('S1');data=snapshot('S1b')
            mode='교육용 승인 예시 체크포인트; 학습자 자동 승인 아님'
            if a.approved_f04:
                text=a.approved_f04.read_text(encoding='utf-8').strip();row=json.loads(text)
                if row.get('assertion_id')!='F04':raise ValueError('F04 승인 파일이 필요합니다.')
                check_assertions([row],'S1b');data['assertions'][-1]=row;mode='학습자가 검토한 F04: '+str(a.approved_f04)
            s1b=run('S1b',data);s1b['input_kind']=mode
            save(ROOT,'S1_log.json',s1);save(ROOT,'S1b_log.json',s1b);save(ROOT,'S1b_input.json',data)
            save(ROOT,'comparison.json',{'S1':s1['calls'][0]['output']['services'],'S1b':s1b['calls'][0]['output']['services'],
                 'notify_path':s1b['calls'][-1]['output']['assertion_ids'],'input_kind':mode})
        else:
            llm(ROOT,a,'prompts/decision.txt',[ROOT/n for n in ['S1_log.json','S1b_log.json','F04_pending.json','raw/RUN-02_v1.md','raw/OPS-04_v1.md']],'decision.md')
    if a.task=='inspect':
        print('7교시 inspect 완료: S1의 실제 호출 인자·결과·전체 원문 인용을 S1_log.json에 저장했습니다.')
    elif a.task!='extract':
        print('7교시 완료. S1/S1b 각각 호출 예산 6회, 실제 도구 로그 저장.')

if __name__=='__main__':
    try:main()
    except (OSError,ValueError,RuntimeError) as e:raise SystemExit(str(e))
