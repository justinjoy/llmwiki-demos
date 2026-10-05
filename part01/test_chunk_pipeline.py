"""Offline integration tests using a real subprocess as the LLM CLI."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import chunk_pipeline as pipeline
import run_lesson1

FAKE = r'''
import json,sys
from pathlib import Path
config=json.loads(Path(__file__).with_suffix('.json').read_text())
p=sys.argv[sys.argv.index('-p')+1]
blocks=json.loads(p.split('참고 파일(JSON):\n',1)[1])
x=json.loads(blocks[0]['content'])
stage='map' if '단계: map\n' in p else 'reduce' if '단계: reduce\n' in p else 'final'
with Path(__file__).with_suffix('.jsonl').open('a') as f:f.write(json.dumps({'stage':stage,'prompt':p,'payload':x})+'\n')
if config.get('fail')==stage:sys.exit(7)
if config.get('oversize')==stage:print('x'*16001);sys.exit()
if stage=='map':
    if config.get('malformed'):print('not json');sys.exit()
    quote=x['content'].strip()[:config.get('quote_chars',160)]
    if config.get('badquote'):quote='invented evidence'
    count=config.get('count',1)
    print(json.dumps({'evidence':[{'quote':quote,'finding':quote[:300]} for _ in range(count)]},ensure_ascii=False))
elif stage=='reduce':
    bad=config.get('badkeep')
    if bad: print(json.dumps({'keep':{'empty':[],'unknown':['fake'],'duplicate':[x['items'][0]['id']]*2,'large':[v['id'] for v in x['items']]}[bad]}));sys.exit()
    keep=[];cost=0
    for e in sorted(x['items'],key=lambda e:e['cost']):
        if cost+e['cost']<=x['target_cost']:keep.append(e['id']);cost+=e['cost']
    print(json.dumps({'keep':keep}))
else:
    if config.get('badcsv'):print('질문,위키 경로,원문 위치,답,남은 확인\n"unterminated');sys.exit()
    if config.get('badfinal'):print('# 잘못된 결과\n[없는 파일](missing.md)');sys.exit()
    if x['output'].endswith('.csv'):
        print('질문,위키 경로,원문 위치,답,남은 확인\n질문1,wiki/services/pay.md,ARCH-01 v1 §1,초안,검토\n질문2,wiki/incidents/INC-03.md,INC-03 v1 §3,초안,검토\n질문3,wiki/services/order.md,ADR-07 v1 §2,초안,검토')
    else:print('# 생성된 초안\n근거를 원문과 검토하세요.')
'''


class ChunkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='chunk 한글 ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fake = self.root / 'fake.py'; self.fake.write_text(FAKE)
        self.config = self.fake.with_suffix('.json'); self.config.write_text('{}')
        self.prompt = self.root / 'prompt.txt'; self.prompt.write_text('원문으로 위키 작성. "인용"과 버전 유지.')
        self.raw = self.root / 'raw.md'; self.raw.write_text('# 제목\n문서 번호: DOC v1\n\n## 절 1\n' + '가나다 본문.\n' * 130)
        self.args = argparse.Namespace(prompt=str(self.prompt), context=[str(self.raw)], output=str(self.root/'out.md'),
            source_root=str(self.root), derived_context=[], cli=sys.executable, cli_arg=[str(self.fake)], mode='print',
            timeout=5, log_dir=str(self.root/'runs'), overwrite=True, dry_run=False,
            chunk_chars=200, max_prompt_chars=16000, max_calls=256)

    def execute(self, budget=None):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return pipeline.execute(self.args, budget)

    def config_set(self, **kw):
        self.config.write_text(json.dumps(kw))

    def manifests(self):
        return [json.loads(p.read_text()) for p in (self.root/'runs').glob('chunk-*/manifest.json')]

    def calls(self):
        p = self.fake.with_suffix('.jsonl')
        return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []

    def test_exact_coverage_unicode_long_lines_sections(self):
        text = '# 문서\n문서 번호: D v2\n\n## 절\n' + '한글"\\' * 1000
        chunks = pipeline.split_source(self.raw, self.root, 100, 'raw', text)
        self.assertEqual(''.join(c['content'] for c in chunks), text)
        self.assertGreater(len(chunks), 2)
        for c in chunks:
            self.assertLessEqual(len(c['content']), 100)
            self.assertEqual(c['content'], text[c['start']:c['end']])
            self.assertEqual(c['line_start'], text.count('\n', 0, c['start']) + 1)
        self.assertEqual(chunks, pipeline.split_source(self.raw, self.root, 100, 'raw', text))
        self.assertEqual(pipeline.split_source(self.raw,self.root,100,'raw',''), [])
        with self.assertRaises(ValueError):pipeline.split_source(self.raw,self.root,100,'raw','#'+'a'*801+'\n## 절\n')

    def test_real_subprocess_maps_final_and_provenance(self):
        original = self.raw.read_bytes()
        self.assertEqual(self.execute(), 0)
        calls = self.calls()
        self.assertGreater(sum(c['stage']=='map' for c in calls), 2)
        for c in calls:
            self.assertLessEqual(len(c['prompt']), self.args.max_prompt_chars)
        final = calls[-1]['payload']
        self.assertNotIn('content', final)
        for e in final['evidence']:
            self.assertIn(e['quote'], self.raw.read_text())
            self.assertEqual(e['source']['source_kind'], 'raw')
        self.assertEqual(self.raw.read_bytes(), original)
        self.assertIn('사람 검토 전', Path(self.args.output).read_text())
        self.assertEqual(self.manifests()[0]['status'], 'success')

    def test_multiple_reduction_rounds_are_bounded_and_audited(self):
        self.raw.write_text('# 문서\n문서 번호: D v1\n\n' + ''.join('## 절 '+str(i)+'\n'+'가나다 문맥.\n'*12 for i in range(24)))
        self.config_set(count=2)
        self.args.max_prompt_chars=7000
        self.assertEqual(self.execute(),0)
        calls=self.calls()
        reduces=[c for c in calls if c['stage']=='reduce']
        self.assertGreater(len(reduces),2)
        # A later reducer sees IDs retained by earlier reducers (multiple rounds).
        earlier=set(); repeated=False
        for c in reduces:
            ids={i['id'] for i in c['payload']['items']}
            repeated |= bool(ids & earlier); earlier.update(ids)
        self.assertTrue(repeated)
        self.assertTrue(all(len(c['prompt'])<=7000 for c in calls))
        manifest=self.manifests()[0]
        self.assertTrue(manifest['omitted_ids'])
        self.assertIn('크기 제한으로 제외',Path(self.args.output).read_text())
        self.assertEqual(len(manifest['selected_ids'])+len(manifest['omitted_ids']),sum(len(c['payload']['content'])>=0 for c in calls if c['stage']=='map')*2)

    def test_map_final_and_validation_failures_preserve_existing(self):
        for config in [{'fail':'map'}, {'fail':'final'}, {'badquote':True}, {'malformed':True}, {'oversize':'map'}, {'oversize':'final'}, {'badfinal':True}]:
            with self.subTest(config=config):
                Path(self.args.output).write_text('keep')
                self.config.write_text(json.dumps(config))
                with self.assertRaises(ValueError):self.execute()
                self.assertEqual(Path(self.args.output).read_text(),'keep')

    def test_invalid_reduce_selections_and_final_failure_after_reduce(self):
        self.raw.write_text('# 文\n' + ''.join('## 절 '+str(i)+'\n'+'long evidence 한글.\n'*12 for i in range(12)))
        self.args.max_prompt_chars=6000
        for config in [{'badkeep':x} for x in ['empty','unknown','duplicate','large']] + [{'fail':'final'}]:
            with self.subTest(config=config):
                Path(self.args.output).write_text('keep')
                self.config.write_text(json.dumps(config))
                with self.assertRaises(ValueError):self.execute()
                self.assertEqual(Path(self.args.output).read_text(),'keep')
        self.assertTrue(any(c['stage']=='reduce' for c in self.calls()))

    def test_dry_run_no_calls_or_results_and_deferred_final(self):
        self.args.dry_run=True;self.args.cli='nonexistent-cli'
        self.assertEqual(self.execute(),0)
        self.assertFalse(Path(self.args.output).exists());self.assertFalse(self.calls())
        self.assertEqual(self.manifests()[0]['final'],'deferred_until_map_results')
        inputs=list((self.root/'runs').glob('chunk-*/*/transport/*/input.txt'))
        self.assertGreater(len(inputs),2)
        self.assertTrue(all(len(p.read_text())<=self.args.max_prompt_chars for p in inputs))

    def test_call_budget_shared_across_tasks(self):
        self.args.max_calls=2
        budget={'used':1};Path(self.args.output).write_text('keep')
        with self.assertRaises(ValueError):self.execute(budget)
        self.assertEqual(budget['used'],2)
        self.assertEqual(len(self.calls()),1)
        self.assertEqual(Path(self.args.output).read_text(),'keep')

    def test_oversized_task_preflight_and_invalid_inputs(self):
        self.prompt.write_text('x'*15000)
        self.args.max_prompt_chars=4000
        with self.assertRaises(ValueError):self.execute()
        self.assertFalse(self.calls())
        self.prompt.write_text('task');self.raw.write_text('')
        with self.assertRaises(ValueError):self.execute()
        self.raw.write_text('x');self.args.chunk_chars=0
        with self.assertRaises(ValueError):self.execute()

    def test_six_task_lesson_with_derived_inputs(self):
        lesson=self.root/'lesson';shutil.copytree(Path(run_lesson1.__file__).parent,lesson,ignore=shutil.ignore_patterns('runs','__pycache__'))
        argv=['run_lesson1.py','--cli',sys.executable,'--cli-arg='+str(self.fake),'--task','all','--overwrite']
        raw_before={p.name:p.read_bytes() for p in (lesson/'raw').glob('*.md')}
        with patch.object(run_lesson1,'LESSON',lesson),patch.object(run_lesson1,'RAW',list((lesson/'raw').glob('*.md'))),patch.object(sys,'argv',argv),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run_lesson1.main(),0)
        finals=[c for c in self.calls() if c['stage']=='final']
        self.assertEqual(len(finals),6)
        self.assertTrue(any(c['payload'].get('source_kind')=='derived' for c in self.calls()))
        self.assertEqual(raw_before,{p.name:p.read_bytes() for p in (lesson/'raw').glob('*.md')})
        for _,output,_ in run_lesson1.TASKS.values():self.assertTrue((lesson/output).stat().st_size)
        manifests=[json.loads(p.read_text()) for p in (lesson/'runs').glob('*/manifest.json')]
        self.assertEqual(max(m['calls_used_total'] for m in manifests),len(self.calls()))

    def test_singleton_cannot_fit_without_silent_truncation(self):
        # One large exact quote fits map, but quote plus explanation/provenance
        # cannot fit final. No reducer may drop the only record silently.
        self.raw.write_text('한' * 3900)
        self.args.chunk_chars = 4000
        self.args.max_prompt_chars = 5000
        self.config_set(quote_chars=3900)
        Path(self.args.output).write_text('keep')
        with self.assertRaises(ValueError):self.execute()
        self.assertEqual(Path(self.args.output).read_text(),'keep')
        self.assertFalse(any(c['stage']=='final' for c in self.calls()))

    def test_malformed_csv_records_error_and_preserves_result(self):
        self.args.output=str(self.root/'out.csv')
        Path(self.args.output).write_text('keep')
        self.config_set(badcsv=True)
        with self.assertRaises(ValueError):self.execute()
        self.assertEqual(Path(self.args.output).read_text(),'keep')
        self.assertEqual(self.manifests()[0]['status'],'error')

    def test_final_format_validation(self):
        with self.assertRaises(ValueError):pipeline.validate_final('invalid',self.root/'out.csv',[self.raw],self.root)
        with self.assertRaises(ValueError):pipeline.validate_final('# T\n[bad][ref]\n[ref]: absent',self.root/'out.md',[self.raw],self.root)
        pipeline.validate_final('# T\n[원문](raw.md)',self.root/'out.md',[self.raw],self.root)


if __name__=='__main__':unittest.main()
