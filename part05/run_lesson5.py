"""5교시: 실제 Wirelog 재귀 질의와 S1/S2/S3 비교, PyreWire 동일 세션 철회."""
import argparse
import csv
from functools import partial
import io
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'shared'))
from lab import snapshot,engine,save
from session_delta import run_delta
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--task',choices=['reason','compare','delta','all'],default='all')
    a=p.parse_args()
    model=(ROOT/'model.dl').read_text(encoding='utf-8');rules=(ROOT/'rules.dl').read_text(encoding='utf-8')
    names=['S1'] if a.task=='reason' else ['S1','S2','S3'] if a.task in ['compare','all'] else []
    comparisons=[]
    for name in names:
        data=snapshot(name);save(ROOT,f'snapshots/{name}.json',data)
        r=engine(ROOT,data,model,rules,output=f'{name}_result.json');rel=r['relations']
        count=(len(rel.get('direct',[])),len(rel.get('reach',[])),len(rel.get('candidate',[])),len(rel.get('candidate_doc',[])))
        expected={'S1':(3,6,3,3),'S2':(4,6,3,3),'S3':(3,5,2,1)}[name]
        if count!=expected:raise ValueError(f'{name}: 예상 {expected}, 실제 {count}')
        comparisons.append([name,data['snapshot_kind'],*count,','.join(x[0] for x in rel['candidate'])])
    if comparisons:
        buf=io.StringIO();w=csv.writer(buf);w.writerow(['snapshot','kind','direct','reach','candidate','candidate_doc','services']);w.writerows(comparisons)
        save(ROOT,'comparison.csv',buf.getvalue())
    if a.task in ['delta','all']:
        result=run_delta(progress=partial(print,flush=True))
        saved=save(ROOT,'delta_run.json',result)
        print(f'[저장 완료] {saved}',flush=True)
        lines=[]
        for i,step in enumerate(result['steps'],1):
            lines.append(f"step {i}: {step['action']}")
            for relation,row,diff in step['events']:
                lines.append(f"{'+' if diff>0 else '-'} {relation}{tuple(row)} (diff={diff})")
            if not step['events']:lines.append('no change')
        saved=save(ROOT,'delta_actual.txt','\n'.join(lines)+'\n')
        print(f'[저장 완료] {saved}',flush=True)
    completed={'reason':'S1 스냅샷 추론 결과', 'compare':'S1/S2/S3 스냅샷 비교 결과',
               'delta':'동일 세션 delta 결과', 'all':'PyreWire 스냅샷 재평가와 동일 세션 delta 결과'}
    print(f'5교시 완료: {completed[a.task]}를 저장했습니다.')

if __name__=='__main__':
    try:main()
    except (OSError,ValueError,RuntimeError) as e:raise SystemExit(str(e))
