"""Offline transport tests: python3 -m unittest discover -s . -p 'test_*.py'."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import run_prompt


class PromptRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="한글 실습 ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prompt = self.root / "prompt.txt"
        self.prompt.write_text('요약해 주세요. $(echo BAD) `echo BAD` "따옴표"', encoding="utf-8")
        self.raw = self.root / "raw.md"
        self.raw.write_text("원문 3초\n인용과 절", encoding="utf-8")
        self.fake = self.root / "fake.py"
        self.fake.write_text("import sys\np=sys.argv[sys.argv.index('-p')+1]\nassert '원문 3초' in p\nassert '$(echo BAD)' in p\nprint('```markdown\\n# 결과\\n검토 전 초안\\n```')\n", encoding="utf-8")
        self.args = argparse.Namespace(prompt=str(self.prompt), context=[str(self.raw)],
            output=str(self.root / "result.md"), cli=sys.executable, cli_arg=[str(self.fake)],
            mode="print", timeout=5, log_dir=str(self.root / "runs"), overwrite=False, dry_run=False)

    def execute(self):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return run_prompt.execute(self.args)

    def latest(self):
        return max((self.root / "runs").iterdir(), key=lambda p: p.stat().st_mtime_ns)

    def test_success_utf8_quoting_and_backup(self):
        output = Path(self.args.output)
        output.write_text("기존 기록", encoding="utf-8")
        self.args.overwrite = True
        self.assertEqual(self.execute(), 0)
        self.assertEqual(output.read_text(), "# 결과\n검토 전 초안\n")
        self.assertEqual((self.latest() / "previous.md").read_text(), "기존 기록")
        self.assertEqual(self.raw.read_text(), "원문 3초\n인용과 절")
        self.assertEqual(json.loads((self.latest() / "run.json").read_text())["status"], "success")

    def test_existing_file_requires_overwrite(self):
        Path(self.args.output).write_text("keep")
        with self.assertRaises(ValueError):
            self.execute()
        self.assertFalse((self.root / "runs").exists())

    def test_failed_cli_preserves_file(self):
        self.fake.write_text("import sys\nprint('partial')\nprint('login required',file=sys.stderr)\nsys.exit(7)")
        Path(self.args.output).write_text("keep")
        self.args.overwrite = True
        self.assertEqual(self.execute(), 7)
        self.assertEqual(Path(self.args.output).read_text(), "keep")
        self.assertIn("login required", (self.latest() / "stderr.txt").read_text())

    def test_empty_response(self):
        self.fake.write_text("print('   ')")
        with self.assertRaises(ValueError):
            self.execute()
        self.assertFalse(Path(self.args.output).exists())

    def test_timeout(self):
        self.fake.write_text("import time\ntime.sleep(5)")
        self.args.timeout = 0.1
        self.assertEqual(self.execute(), 124)
        self.assertFalse(Path(self.args.output).exists())

    def test_dry_run_needs_no_cli_and_changes_no_result(self):
        self.args.cli = "this-cli-is-not-installed"
        self.args.dry_run = True
        self.assertEqual(self.execute(), 0)
        self.assertIn("원문 3초", (self.latest() / "input.txt").read_text())
        self.assertFalse(Path(self.args.output).exists())

    def test_missing_context_stops_before_call(self):
        self.args.context.append(str(self.root / "missing.md"))
        with self.assertRaises(FileNotFoundError):
            self.execute()
        self.assertFalse((self.root / "runs").exists())

    def test_input_cannot_be_output(self):
        self.args.output = str(self.raw)
        self.args.overwrite = True
        with self.assertRaises(ValueError):
            self.execute()

    def test_codex_stdin_adapter_and_print_adapters(self):
        cmd, stdin = run_prompt.cli_command("codex", [], "auto", "긴 입력")
        self.assertEqual(cmd[1], "exec")
        self.assertEqual(cmd[-1], "-")
        self.assertNotIn("-p", cmd)
        self.assertEqual(stdin, "긴 입력")
        for cli in ["claude", "cursor-agent", "copilot", "agy"]:
            cmd, stdin = run_prompt.cli_command(cli, [], "auto", "내용")
            self.assertEqual(cmd[-2:], ["-p", "내용"])
            self.assertEqual(stdin, "")


if __name__ == "__main__":
    unittest.main()
