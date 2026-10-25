"""One PyreWire session: insert, no-change, retract (+2 / 0 / -2)."""
from importlib.metadata import version
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'shared'))
from query import require_pyrewire

SOURCE = '''.decl friend(a: symbol, b: symbol)
.decl mutual(a: symbol, b: symbol)
mutual(A, B) :- friend(A, B), friend(B, A).
'''


def run_delta(progress=None):
    """Run the demo, optionally reporting progress through a text callback."""
    def report(message):
        if progress is not None:
            progress(message)

    def record_step(session, action):
        report('  session.step(): 추론 변화 계산')
        events = session.step()
        steps.append({'action': action, 'events': events})
        for relation, row, diff in events:
            report(f"  {'+' if diff > 0 else '-'} {relation}{tuple(row)} (diff={diff})")
        if not events:
            report('  no change: mutual 변화 없음')

    report('[delta] PyreWire 준비: 하나의 EasySession에서 추가·삭제를 차례로 적용합니다.')
    EasySession, WirelogError = require_pyrewire()
    steps = []
    report('[규칙] mutual(A, B) :- friend(A, B), friend(B, A).')
    report('  양방향 friend가 모두 있어야 mutual이 성립합니다.')
    try:
        with EasySession(SOURCE) as session:
            report('[1/3] 양방향 친구 관계 추가')
            report("  insert friend('alice', 'bob')")
            session.insert('friend', ['alice', 'bob'])
            report("  insert friend('bob', 'alice')")
            session.insert('friend', ['bob', 'alice'])
            record_step(session, 'insert both directions')
            report('[2/3] 한쪽 방향만 추가: 역방향이 없어 새로운 mutual은 성립하지 않습니다.')
            report("  insert friend('alice', 'carol')")
            session.insert('friend', ['alice', 'carol'])
            record_step(session, 'insert one direction')
            report('[3/3] 역방향 관계 삭제: 양방향 조건이 깨져 기존 mutual을 철회합니다.')
            report("  remove friend('bob', 'alice')")
            session.remove('friend', ['bob', 'alice'])
            record_step(session, 'remove reverse direction')
    except WirelogError as exc:
        raise RuntimeError(f'PyreWire {type(exc).__name__}: {exc}') from exc
    expected = [[('mutual', ('alice', 'bob'), 1), ('mutual', ('bob', 'alice'), 1)], [],
                [('mutual', ('alice', 'bob'), -1), ('mutual', ('bob', 'alice'), -1)]]
    if [sorted(step['events']) for step in steps] != expected:
        raise ValueError(f'Unexpected incremental events: {steps}')
    report('[검증 완료] 실제 mutual 이벤트가 +2 / 0 / -2와 일치합니다.')
    return {'status': 'success', 'engine': 'pyrewire', 'engine_version': version('pyrewire'),
            'mode': 'same_session_EasySession.step', 'steps': steps}

if __name__ == '__main__':
    import json
    print(json.dumps(run_delta(), ensure_ascii=False, indent=2))
