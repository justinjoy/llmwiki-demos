"""4교시: 승인 입력 적재, 기본·추가 질의, 잘못된 입력의 실제 실행 비교."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'shared'))
from lab import snapshot, check_assertions, facts_text, engine, evaluate, save
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--task',choices=['query','extend','invalid','all'],default='all')
    p.add_argument('--assertions',type=Path,help='3교시에서 사람이 승인한 JSONL; 생략하면 교육용 S1 체크포인트')
    a=p.parse_args();data=snapshot('S1')
    if a.assertions:
        sys.path.insert(0,str(ROOT.parent/'part03'))
        from review_workflow import verify_export_file
        data['assertions']=verify_export_file(a.assertions)
        check_assertions(data['assertions'])
        data['input_kind']='사용자가 지정한 승인 파일: '+str(a.assertions.resolve())
    save(ROOT,'input.json',data)
    facts=facts_text(data);save(ROOT,'facts.dl',facts)
    model=(ROOT/'model.dl').read_text(encoding='utf-8')
    if a.task in ['query','all']:
        save(ROOT,'lesson.dl',model+'\n'+facts)
        result=engine(ROOT,data,model)
        expected=sorted({(r['subject'],r['object']) for r in data['assertions']})
        if result['relations'].get('direct') != [list(r) for r in expected]: raise ValueError('direct와 승인 사실 불일치')
        if result['relations'].get('pay_doc') != [['ARCH-01:v1'],['INC-03:v1']]: raise ValueError('pay_doc 결과 불일치')
    if a.task in ['extend','all']:
        result=engine(ROOT,data,model,(ROOT/'queries.dl').read_text(),output='extended_result.json')
        if result['relations'].get('order_doc') != [['ADR-07:v1']]: raise ValueError('order_doc 결과 불일치')
    if a.task in ['invalid','all']:
        broken=model+'\ndepends_on("pay").\n';save(ROOT,'errors/wrong_arity.dl',broken)
        try: evaluate(broken,'')
        except (RuntimeError,ValueError) as exc:
            save(ROOT,'invalid_result.json',{'status':'expected_error','kind':'arity','message':str(exc)})
        else: raise ValueError('열 수 오류가 검출되지 않았습니다.')
        reversed_facts=facts.replace('depends_on("order", "pay").','depends_on("pay", "order").')
        save(ROOT,'errors/reversed_direction.dl',model+'\n'+reversed_facts)
        result=evaluate(model,reversed_facts)
        result['lesson']='두 열 모두 symbol이므로 역방향도 실행 성공. 원문·관계 사전과 대조해야 의미 오류를 찾습니다.'
        save(ROOT,'direction_result.json',result)
    print('4교시 완료: 결과와 runs/의 실제 PyreWire 입력·결과를 확인하세요.')

if __name__=='__main__':
    try:main()
    except (OSError,ValueError,RuntimeError) as e:raise SystemExit(str(e))
