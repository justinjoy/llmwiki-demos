import contextlib
import csv
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_workflow import ROOT, Store
from review_walkthrough import edit_sheet, read_sheet, run_walkthrough


class CsvWalkthroughTests(unittest.TestCase):
    def test_auto_demo_imports_real_csv_and_preserves_original(self):
        original = (ROOT / 'review.csv').read_bytes()
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            with patch.object(Store, 'decide', side_effect=AssertionError('CSV를 거치지 않은 판정')):
                self.assertEqual(run_walkthrough(Path(folder)), {'approved': 3, 'held': 1, 'rejected': 5})
            work = Path(folder)
            before = next(r for r in read_sheet(work / '01-reject-before.csv') if r['id'] == 'F03')
            after = next(r for r in read_sheet(work / '01-reject-edited.csv') if r['id'] == 'F03')
            self.assertEqual((before['판정'], after['판정']), ('pending', 'rejected'))
            for field in ('id', 'revision', 'content_sha256'):
                self.assertEqual(before[field], after[field])
            history = Store(work).history('F03')
            self.assertEqual([r['status'] for r in history], [None, 'rejected', 'approved'])
        self.assertEqual((ROOT / 'review.csv').read_bytes(), original)

    def test_interactive_waits_for_edit_and_retries_invalid_csv(self):
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(output):
            work = Path(folder)
            calls = []

            def edit_when_prompted(prompt):
                calls.append(prompt)
                store = Store(work)
                row = next(r for r in store.current() if r['id'] == 'F03')
                if len(calls) == 1:
                    self.assertEqual(row['status'], 'pending')
                    return ''  # No CSV edit: must retry without saving a decision.
                if row['revision'] == 2:
                    self.assertEqual(row['status'], 'pending')
                    edits = {'F03': ('rejected', 'ARCH-01 v1 §2: 호출 방향 반대')}
                else:
                    with (ROOT / 'review.example.csv').open(newline='') as stream:
                        edits = {r['id']: (r['판정'], r['근거 또는 이유']) for r in csv.DictReader(stream)}
                edit_sheet(work / 'review.csv', edits)
                return ''

            counts = run_walkthrough(work, interactive=True, wait=edit_when_prompted)
            self.assertEqual(len(calls), 3)
            self.assertEqual(counts['approved'], 3)
            self.assertIn('반영하지 못했습니다', output.getvalue())
            self.assertTrue((work / '02-rereview-edited.csv').exists())

    def test_all_tasks_offer_csv_import_after_generation(self):
        import run_lesson3
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ('assertions.jsonl', 'aliases.json', 'entities.json', 'error_candidates.json'):
                (root / name).write_text('{}')
            store = Mock()
            store.db.exists.return_value = False
            store.sheet = root / 'review.csv'
            output = io.StringIO()
            with patch.object(run_lesson3, 'LESSON', root), \
                 patch.object(run_lesson3.run_prompt, 'execute', return_value=0) as execute, \
                 patch.object(run_lesson3, 'validate_output'), \
                 patch('review_workflow.Store', return_value=store), \
                 patch.object(sys, 'argv', ['run_lesson3.py', '--cli', 'agy', '--task', 'all', '--overwrite']), \
                 contextlib.redirect_stdout(output):
                self.assertEqual(run_lesson3.main(), 0)
            self.assertEqual(execute.call_count, 4)
            store.init.assert_called_once_with()
            self.assertIn(str(store.sheet), output.getvalue())
            self.assertIn('review_workflow.py import-review', output.getvalue())
            self.assertIn('review_walkthrough.py --interactive', output.getvalue())

    def test_quit_preserves_pending_workspace(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            work = Path(folder)
            with self.assertRaises(InterruptedError):
                run_walkthrough(work, interactive=True, wait=lambda prompt: 'q')
            self.assertTrue((work / 'review.csv').exists())
            self.assertTrue(all(r['status'] == 'pending' for r in Store(work).current()))


if __name__ == '__main__':
    unittest.main()
