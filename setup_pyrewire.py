"""Check the pinned PyreWire installation and a real symbol query."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / 'shared'))
from query import evaluate

if __name__ == '__main__':
    result = evaluate('.decl edge(a:symbol,b:symbol)\n.decl direct(a:symbol,b:symbol)\ndirect(A,B):-edge(A,B).',
                      'edge("pay","ledger").')
    assert result['relations']['direct'] == [['pay', 'ledger']]
    import pyrewire
    print('PyreWire', result['engine_version'], 'ready:', pyrewire.__file__)
