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


def run_delta():
    EasySession, WirelogError = require_pyrewire()
    steps = []
    try:
        with EasySession(SOURCE) as session:
            session.insert('friend', ['alice', 'bob'])
            session.insert('friend', ['bob', 'alice'])
            steps.append({'action': 'insert both directions', 'events': session.step()})
            session.insert('friend', ['alice', 'carol'])
            steps.append({'action': 'insert one direction', 'events': session.step()})
            session.remove('friend', ['bob', 'alice'])
            steps.append({'action': 'remove reverse direction', 'events': session.step()})
    except WirelogError as exc:
        raise RuntimeError(f'PyreWire {type(exc).__name__}: {exc}') from exc
    expected = [[('mutual', ('alice', 'bob'), 1), ('mutual', ('bob', 'alice'), 1)], [],
                [('mutual', ('alice', 'bob'), -1), ('mutual', ('bob', 'alice'), -1)]]
    if [sorted(step['events']) for step in steps] != expected:
        raise ValueError(f'Unexpected incremental events: {steps}')
    return {'status': 'success', 'engine': 'pyrewire', 'engine_version': version('pyrewire'),
            'mode': 'same_session_EasySession.step', 'steps': steps}

if __name__ == '__main__':
    import json
    print(json.dumps(run_delta(), ensure_ascii=False, indent=2))
