"""Evaluate Datalog directly with PyreWire 1.1.2; no CLI or simulated fallback."""
import argparse
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import re

REQUIRED_VERSION = '1.1.2'
# Register literals through the public interning API so snapshot rows contain
# original symbols. Skip comments; never infer numeric symbol IDs ourselves.
TOKENS = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"', re.DOTALL)


def require_pyrewire():
    try:
        installed = version('pyrewire')
    except PackageNotFoundError as exc:
        raise RuntimeError('python3 -m pip install pyrewire==1.1.2 를 먼저 실행하세요.') from exc
    if installed != REQUIRED_VERSION:
        raise RuntimeError(f'PyreWire {REQUIRED_VERSION} 필요; 현재 {installed}')
    from pyrewire import EasySession, WirelogError
    return EasySession, WirelogError


def evaluate(model, facts, rules=''):
    EasySession, WirelogError = require_pyrewire()
    source = model + '\n' + facts + '\n' + rules
    clean = TOKENS.sub(' ', source)
    names = list(dict.fromkeys(re.findall(r'\.decl\s+(\w+)\s*\(', clean, re.MULTILINE)))
    try:
        with EasySession(source) as session:
            for token in TOKENS.finditer(source):
                if token[0].startswith('"'):
                    session.intern(json.loads(token[0]))
            relations = {}
            for name in names:
                rows = session.snapshot(name)
                if rows:
                    relations[name] = [list(row) for row in sorted(set(rows))]
    except WirelogError as exc:
        raise RuntimeError(f'PyreWire {type(exc).__name__}: {exc}') from exc
    return {'status': 'success', 'engine': 'pyrewire', 'engine_version': REQUIRED_VERSION,
            'api': 'EasySession.snapshot', 'relations': relations}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model', required=True, type=Path)
    p.add_argument('--facts', required=True, type=Path)
    p.add_argument('--rules', type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    try:
        result = evaluate(a.model.read_text(encoding='utf-8'), a.facts.read_text(encoding='utf-8'),
                          a.rules.read_text(encoding='utf-8') if a.rules else '')
    except (OSError, ValueError, RuntimeError) as exc:
        result = {'status': 'error', 'message': str(exc)}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['status'] == 'success' else 1)

if __name__ == '__main__':
    main()
