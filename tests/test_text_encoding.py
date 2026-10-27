"""Exercise UTF-8 lesson files with a CP949 default, on any platform."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = """
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
from unittest.mock import patch

repo = Path(sys.argv[1])
sys.path.insert(0, str(repo / 'shared'))
sys.path.insert(0, str(repo / 'part03'))
original_text_encoding = io.text_encoding
io.text_encoding = lambda encoding, *args: original_text_encoding(
    'cp949' if encoding is None else encoding, *args)
# Prove that the simulated file default actually rejects our UTF-8 data.
control = Path('control.txt')
control.write_bytes('한글 원문'.encode('utf-8'))
try:
    control.read_text()
except UnicodeDecodeError:
    pass
else:
    raise AssertionError('CP949 control read unexpectedly succeeded')
"""


class TextEncodingTests(unittest.TestCase):
    def run_case(self, source):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run(
                [sys.executable, '-X', 'utf8=0', '-c', BOOTSTRAP + textwrap.dedent(source), str(ROOT)],
                cwd=folder, env=dict(os.environ, PYTHONUTF8='0', PYTHONIOENCODING='utf-8'),
                capture_output=True, encoding='utf-8', timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_review_initialization_revision_and_export(self):
        self.run_case("""
            import review_workflow as review
            root = Path('review')
            root.mkdir()
            for name in ('assertions.jsonl', 'error_candidates.json'):
                shutil.copy2(repo / 'part03' / name, root / name)
            shutil.copytree(repo / 'part03/raw', root / 'raw')
            store = review.Store(root)
            store.init()
            assert len(store.current()) == 9
            payload = json.loads(next(r for r in store.current() if r['id'] == 'F03')['payload'])
            payload['scope'] += ' / 수정 확인'
            revision = root / 'revision.json'
            revision.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
            with patch.object(sys, 'argv', ['review_workflow.py', '--root', str(root),
                    'revise', 'F03', '--revision', '1', '--file', str(revision),
                    '--actor', '검토자', '--reason', '원문 확인']):
                review.main()
            assert '수정 확인' in next(r for r in store.current() if r['id'] == 'F03')['payload']
            for row in store.current():
                store.decide(row['id'], row['revision'], 'rejected', '검토자', '인코딩 테스트')
            store.export(overwrite=True)
            assert review.verify_export_file(root / 'approved.jsonl') == []
        """)

    def test_wiki_dry_run_and_finalization(self):
        self.run_case("""
            spec = importlib.util.spec_from_file_location('lesson8', repo / 'part08/run_lesson8.py')
            lesson = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(lesson)
            root = Path('part08').resolve()
            shutil.copytree(repo / 'part08', root, ignore=shutil.ignore_patterns('runs', '__pycache__'))
            lesson.ROOT = root
            with patch.object(sys, 'argv', ['run_lesson8.py', '--task', 'wiki', '--dry-run']):
                lesson.main()
            before = {p.relative_to(root).as_posix(): p.read_text(encoding='utf-8')
                      for p in (root / 'wiki').rglob('*.md')}
            page = root / 'wiki/analysis/ledger-impact-S1b.md'
            page.write_text(page.read_text(encoding='utf-8') + '\\n추가 검토 기록\\n', encoding='utf-8')
            lesson.finish_wiki(before)
            assert '추가 검토 기록' in (root / 'change.diff').read_text(encoding='utf-8')
            assert 'S1b 분석 초안' in (root / 'wiki/log.md').read_text(encoding='utf-8')
        """)

    def test_shared_logs_use_utf8_for_non_cp949_text(self):
        self.run_case("""
            import lab
            root = Path('실습-😀')
            lab.save(root, 'result.txt', '이전 내용')
            lab.save(root, 'result.txt', '새 내용')
            change = json.loads(next((root / 'runs').glob('*/change.json')).read_text(encoding='utf-8'))
            assert '😀' in change['output']
            with patch.object(lab, 'evaluate', side_effect=ValueError('원문 오류 😀')):
                try:
                    lab.engine(root, {'assertions': [], 'about': []}, '')
                except ValueError as exc:
                    assert str(exc) == '원문 오류 😀'
                else:
                    raise AssertionError('Expected engine error')
            record = json.loads(next((root / 'runs').glob('engine-*/run.json')).read_text(encoding='utf-8'))
            assert record['error'] == '원문 오류 😀'
        """)


if __name__ == '__main__':
    unittest.main()
