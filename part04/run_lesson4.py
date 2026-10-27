"""4교시: 승인 입력 적재, 기본·추가 질의, 잘못된 입력의 실제 실행 비교."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'shared'))
from lab import snapshot, check_assertions, facts_text, engine, evaluate, save
ROOT=Path(__file__).resolve().parent

def report(message):
    print(message,flush=True)

def save_report(name,value):
    path=save(ROOT,name,value)
    report(f'[저장 완료] {path}')

def report_relations(result,names):
    for name in names:
        rows=result['relations'].get(name,[])
        report(f'  {name}: {len(rows)}개')
        for row in rows:
            report(f'    {name}{tuple(row)}')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--task',choices=['query','extend','invalid','all'],default='all')
    p.add_argument('--assertions',type=Path,help='3교시에서 사람이 승인한 JSONL; 생략하면 교육용 S1 체크포인트')
    a=p.parse_args()
    report(f'[시작] 4교시 task={a.task}')
    report('[입력] S1 교육용 체크포인트를 읽고 승인 사실을 검증합니다.')
    data=snapshot('S1')
    if a.assertions:
        report(f'[입력] 사용자 승인 파일의 내보내기 상태와 승인 사실 검증: {a.assertions.resolve()}')
        sys.path.insert(0,str(ROOT.parent/'part03'))
        from review_workflow import verify_export_file
        data['assertions']=verify_export_file(a.assertions)
        check_assertions(data['assertions'])
        data['input_kind']='사용자가 지정한 승인 파일: '+str(a.assertions.resolve())
    report(f"[입력 검증 완료] {data.get('input_kind','최종 교육자료의 승인 예시 체크포인트')}; 승인 사실 {len(data['assertions'])}개")
    save_report('input.json',data)
    report('[사실 변환] 승인 관계는 depends_on(src, dst), 문서 연결은 about(doc, svc)로 투영합니다.')
    facts=facts_text(data)
    for relation in ('depends_on','about'):
        rows=[line for line in facts.splitlines() if line.startswith(relation+'(')]
        report(f'  {relation}: {len(rows)}개')
        for row in rows: report('    '+row)
    save_report('facts.dl',facts)
    report(f'[모델] 선언과 기본 질의 규칙 읽기: {ROOT/"model.dl"}')
    model=(ROOT/'model.dl').read_text(encoding='utf-8')
    if a.task in ['query','all']:
        report('[기본 질의] direct는 직접 의존 관계, pay_doc은 pay와 연결된 문서를 조회합니다.')
        save_report('lesson.dl',model+'\n'+facts)
        report('[실행] PyreWire로 모델과 승인 사실을 평가합니다.')
        result=engine(ROOT,data,model)
        report(f'[저장 완료] {ROOT/"result.json"}')
        report_relations(result,('direct','pay_doc'))
        expected=sorted({(r['subject'],r['object']) for r in data['assertions']})
        if result['relations'].get('direct') != [list(r) for r in expected]: raise ValueError('direct와 승인 사실 불일치')
        if result['relations'].get('pay_doc') != [['ARCH-01:v1'],['INC-03:v1']]: raise ValueError('pay_doc 결과 불일치')
        report('[검증 완료] direct가 승인 관계와 일치하고 pay_doc이 ARCH-01:v1, INC-03:v1과 일치합니다.')
    if a.task in ['extend','all']:
        report(f'[추가 질의] 규칙 읽기: {ROOT/"queries.dl"}')
        rules=(ROOT/'queries.dl').read_text(encoding='utf-8')
        report('  order_doc은 order와 연결된 문서, shop_dep은 shop의 직접 의존 대상을 조회합니다.')
        for line in rules.splitlines(): report('    '+line)
        report('[실행] PyreWire로 기본 모델과 추가 질의 규칙을 함께 평가합니다.')
        result=engine(ROOT,data,model,rules,output='extended_result.json')
        report(f'[저장 완료] {ROOT/"extended_result.json"}')
        report_relations(result,('order_doc','shop_dep'))
        if result['relations'].get('order_doc') != [['ADR-07:v1']]: raise ValueError('order_doc 결과 불일치')
        report('[검증 완료] order_doc이 ADR-07:v1과 일치합니다.')
    if a.task in ['invalid','all']:
        report('[오류 실습 1/2] depends_on은 인자 2개가 필요하지만 depends_on("pay").는 1개만 제공합니다.')
        broken=model+'\ndepends_on("pay").\n';save_report('errors/wrong_arity.dl',broken)
        report('[실행] 잘못된 열 수의 입력을 PyreWire에 전달합니다.')
        try: evaluate(broken,'')
        except (RuntimeError,ValueError) as exc:
            report(f'[예상 오류 확인] {exc}')
            save_report('invalid_result.json',{'status':'expected_error','kind':'arity','message':str(exc)})
        else: raise ValueError('열 수 오류가 검출되지 않았습니다.')
        report('[오류 실습 2/2] order → pay 관계를 pay → order로 바꾸어 실행합니다.')
        reversed_facts=facts.replace('depends_on("order", "pay").','depends_on("pay", "order").')
        if reversed_facts==facts:
            report('  변경 대상 order → pay가 입력에 없어 사실을 바꾸지 않고 실행합니다.')
        else:
            report('  depends_on("order", "pay"). → depends_on("pay", "order").')
        save_report('errors/reversed_direction.dl',model+'\n'+reversed_facts)
        report('[실행] 방향 오류 예제의 사실을 PyreWire로 평가합니다.')
        result=evaluate(model,reversed_facts)
        report('[실행 성공] 실제 direct 결과:')
        report_relations(result,('direct',))
        result['lesson']='두 열 모두 symbol이므로 역방향도 실행 성공. 원문·관계 사전과 대조해야 의미 오류를 찾습니다.'
        report('[해설] '+result['lesson'])
        save_report('direction_result.json',result)
    if a.task in ['query','extend','all']:
        report(f'[실행 기록] 기본·추가 질의 중 실행한 평가의 입력·결과: {ROOT/"runs"}/engine-*')
    completed={'query':'기본 질의', 'extend':'추가 질의', 'invalid':'잘못된 열 수와 방향 오류 실습',
               'all':'기본 질의, 추가 질의, 잘못된 열 수와 방향 오류 실습'}
    report(f'4교시 완료: {completed[a.task]} 결과를 저장했습니다.')

if __name__=='__main__':
    try:main()
    except (OSError,ValueError,RuntimeError) as e:raise SystemExit(str(e))
