"""Source provenance and real subprocess tests for adaptive low-call bundles."""
import argparse
import contextlib
import io
import json
import os
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
x=json.loads(json.loads(p.split('참고 파일(JSON):\n',1)[1])[0]['content'])
stage='map' if '단계: map\n' in p else 'final'
with Path(__file__).with_suffix('.jsonl').open('a') as f:f.write(json.dumps({'stage':stage,'prompt':p,'payload':x})+'\n')
if config.get('fail')==stage:sys.exit(7)
if config.get('oversize')==stage:print('x'*16001);sys.exit()
if stage=='map':
    if config.get('malformed'):print('not json');sys.exit()
    items=[]
    for source in x['sources'][:6]:
        quote=source['content'].strip()[:config.get('quote_chars',160)]
        if config.get('badquote') or (config.get('repair_map') and 'validation_feedback' not in x):quote='invented evidence'
        items.append({'source_id':source['id'],'quote':quote,'finding':quote[:300]})
    if config.get('partial_bad') and 'validation_feedback' not in x:
        items.append({'source_id':x['sources'][0]['id'],'quote':'invented evidence','finding':'bad second item'})
    print(json.dumps({'evidence':items},ensure_ascii=False))
else:
    if config.get('badfinal') or (config.get('repair_final') and 'validation_feedback' not in x):print('# 초안\n[없는 파일](missing.md)');sys.exit()
    if config.get('badcsv'):print('질문,위키 경로,원문 위치,답,남은 확인\n"unterminated');sys.exit()
    if x['output'].endswith('.csv'):
        print('질문,위키 경로,원문 위치,답,남은 확인\n질문1,wiki/services/pay.md,ARCH-01 v1 §1,초안,검토\n질문2,wiki/incidents/INC-03.md,INC-03 v1 §3,초안,검토\n질문3,wiki/services/order.md,ADR-07 v1 §2,초안,검토')
    else:print('# 생성된 초안\n근거를 원문과 검토하세요.')
'''


class ChunkTests(unittest.TestCase):
    def setUp(self):
        encoding = patch.dict(os.environ, PYTHONIOENCODING='utf-8')
        encoding.start(); self.addCleanup(encoding.stop)
        tmp = tempfile.TemporaryDirectory(prefix='chunk 한글 ')
        self.addCleanup(tmp.cleanup); self.root = Path(tmp.name)
        self.fake = self.root/'fake.py'; self.fake.write_text(FAKE, encoding='utf-8')
        self.config = self.fake.with_suffix('.json'); self.config_set()
        self.prompt = self.root/'prompt.txt'; self.prompt.write_text('원문으로 위키 작성. "인용"과 버전 유지.', encoding='utf-8')
        self.raw = self.root/'raw.md'; self.raw.write_text('# 문서\n문서 번호: D v1\n\n## 본문\n'+'한글 본문.\n'*130, encoding='utf-8')
        self.args = argparse.Namespace(prompt=str(self.prompt), context=[str(self.raw)], output=str(self.root/'out.md'),
            source_root=str(self.root), derived_context=[], cli=sys.executable, cli_arg=[str(self.fake)], mode='print',
            timeout=5, log_dir=str(self.root/'runs'), overwrite=True, dry_run=False,
            chunk_chars=4800, max_prompt_chars=16000, max_calls=256)

    def config_set(self, **kw):
        self.config.write_text(json.dumps(kw), encoding='utf-8')

    def execute(self, budget=None):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return pipeline.execute(self.args, budget)

    def manifest(self):
        p=max((self.root/'runs').glob('chunk-*/manifest.json'),key=lambda p:p.stat().st_mtime_ns)
        return json.loads(p.read_text())

    def calls(self):
        path=self.fake.with_suffix('.jsonl')
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def document(self, path, text, kind='raw'):
        return pipeline.source_document(path,self.root,kind,text)

    def test_defaults_and_input_validation(self):
        args=pipeline.add_options(argparse.ArgumentParser()).parse_args([])
        self.assertEqual((args.chunk_chars,args.max_prompt_chars),(4800,16000))
        for key,value in [('chunk_chars',0),('max_prompt_chars',3999),('max_calls',0),('timeout',0)]:
            with self.subTest(key=key),patch.object(self.args,key,value),self.assertRaises(ValueError):self.execute()
        self.assertFalse(self.calls())

    def test_balanced_one_two_three_bundles_preserve_exact_files_ranges_and_kinds(self):
        texts=['# 원문\n\n## 첫 절\n'+'가나다\n'*150+'## 다음 절\n끝.\n', '# 파생\n'+'따옴표"\\\n'*90]
        docs=[self.document(self.raw,texts[0]),self.document(self.root/'derived.md',texts[1],'derived')]
        for count in (1,2,3):
            groups=pipeline.bundle_sources(docs,count)
            self.assertEqual(len(groups),count)
            self.assertEqual(groups,pipeline.bundle_sources(docs,count))
            for doc,text in zip(docs,texts):
                fragments=[s for c in groups for s in c['sources'] if s['path']==doc['path']]
                self.assertEqual(''.join(s['content'] for s in fragments),text)
                for s in fragments:
                    self.assertEqual(s['content'],text[s['start']:s['end']])
                    self.assertEqual(s['line_start'],text.count('\n',0,s['start'])+1)
                    self.assertEqual(s['source_kind'],doc['source_kind'])
                    self.assertEqual(s['source_sha256'],doc['source_sha256'])
                    self.assertNotIn('header',s)
        self.assertIn('…',pipeline.bundle_sources(docs,1)[0]['sources'][0]['section'])
        self.assertEqual(pipeline.bundle_sources([],3),[])

    def test_long_lines_unicode_and_metadata_safeguards(self):
        text='긴줄한글"\\'*2000
        docs=[self.document(self.raw,text)]
        groups=pipeline.bundle_sources(docs,3)
        self.assertEqual(''.join(s['content'] for c in groups for s in c['sources']),text)
        for bad in ['#'+'a'*801+'\n## 절\n', '# 문서\n## '+'a'*301+'\n']:
            with self.assertRaises(ValueError):self.document(self.raw,bad)

    def test_wrong_source_unknown_id_other_bundle_and_cross_fragment_quotes_reject(self):
        docs=[self.document(self.raw,'문서 A 고유 원문.'),self.document(self.root/'b.md','문서 B 다른 원문.','derived')]
        chunk=pipeline.bundle_sources(docs,1)[0];first,second=chunk['sources']
        valid={'source_id':first['id'],'quote':'A 고유','finding':'설명'}
        result=pipeline.validate_map(json.dumps({'evidence':[valid]}),chunk)
        self.assertEqual(result[0]['source']['path'],'raw.md')
        for item in [dict(valid,source_id=second['id']),dict(valid,source_id='unknown'),
                     dict(valid,quote=first['content']+second['content']),{'quote':'A 고유','finding':'설명'}]:
            with self.subTest(item=item),self.assertRaises(ValueError):
                pipeline.validate_map(json.dumps({'evidence':[valid,item]}),chunk)
        other=pipeline.bundle_sources(docs,2)[1]
        with self.assertRaises(ValueError):pipeline.validate_map(json.dumps({'evidence':[valid]}),other)

    def test_header_is_not_evidence_outside_its_actual_range(self):
        text='# 문서\n담당: 원문 담당 팀\n\n## 본문\n'+'본문.\n'*100
        groups=pipeline.bundle_sources([self.document(self.raw,text)],3)
        later=groups[-1]['sources'][0]
        response={'evidence':[{'source_id':later['id'],'quote':'담당: 원문 담당 팀','finding':'담당'}]}
        with self.assertRaisesRegex(ValueError,'출처 범위'):pipeline.validate_map(json.dumps(response),groups[-1])

    def test_json_framing_rejects_ambiguous_and_nested_objects(self):
        value={'evidence':[]};body=json.dumps(value,indent=2)
        for text in [body,'설명\n'+body,'설명\n```json\n'+body+'\n```']:
            self.assertEqual(pipeline.json_response(text),value)
        for text in ['설명\n{}\n{}','설명\n{}\n뒤 설명','설명\n{broken\n{}','설명만',
                     '설명 {"evidence": []}\n'+body,'설명\n[\n'+body,'설명 {"outer":\n'+body]:
            with self.subTest(text=text),self.assertRaises(ValueError):pipeline.json_response(text)

    def test_small_task_uses_one_map_and_one_final_with_all_evidence(self):
        before=self.raw.read_bytes();self.assertEqual(self.execute(),0)
        calls=self.calls();self.assertEqual([c['stage'] for c in calls],['map','final'])
        meta=self.manifest();self.assertEqual(meta['initial_map_groups'],1)
        self.assertEqual(meta['selected_ids'],[e['id'] for e in calls[-1]['payload']['evidence']])
        self.assertEqual(meta['omitted_ids'],[]);self.assertEqual(meta['selection'],[])
        self.assertEqual(self.raw.read_bytes(),before)
        self.assertIn('사람 검토 전',Path(self.args.output).read_text())

    def test_larger_inputs_use_two_or_three_groups_and_grow_instead_of_stop(self):
        self.args.chunk_chars=100;self.args.max_prompt_chars=4000
        for repetitions,expected in [(300,2),(3000,3)]:
            self.raw.write_text('# 문서\n\n## 본문\n'+'한글 본문.\n'*repetitions,encoding='utf-8')
            self.assertEqual(self.execute(),0);meta=self.manifest()
            self.assertEqual(meta['initial_map_groups'],expected)
            self.assertLessEqual(len(meta['chunks']),3)
            self.assertEqual(len(meta['calls']),expected+1)
            self.assertEqual(meta['requested_prompt_chars'],4000)
            self.assertTrue(all(c['prompt_chars']<=c['effective_prompt_chars'] for c in meta['calls']))
        self.assertGreater(meta['effective_prompt_chars'],4000)
        self.assertEqual(self.args.max_prompt_chars,4000)

    def test_expanded_map_correction_and_final_capacity_reaches_transport(self):
        self.raw.write_text('# 문서\n\n## 본문\n'+'본문 원문.\n'*3000,encoding='utf-8')
        self.args.chunk_chars=100;self.args.max_prompt_chars=4000
        self.config_set(quote_chars=1200,repair_map=True,repair_final=True)
        self.assertEqual(self.execute(),0)
        meta=self.manifest();self.assertEqual(meta['initial_map_groups'],3)
        self.assertTrue(any(c['attempt']==1 and c['prompt_chars']>4000 for c in meta['calls']))
        final=[c for c in meta['calls'] if c['stage']=='final']
        self.assertEqual(len(final),2);self.assertGreater(final[0]['prompt_chars'],4000)
        self.assertTrue(all(c['status']=='success' for c in meta['calls']))

    def test_retry_validates_whole_response_before_appending_and_is_bounded(self):
        self.config_set(partial_bad=True)
        self.assertEqual(self.execute(),0)
        calls=self.calls();self.assertEqual(len(calls),3)
        self.assertEqual(len(calls[-1]['payload']['evidence']),1)
        self.assertEqual([c['validation_status'] for c in self.manifest()['calls']],['rejected','accepted','accepted'])
        self.config_set(badquote=True);Path(self.args.output).write_text('keep')
        with self.assertRaisesRegex(ValueError,'출처 범위'):self.execute()
        self.assertEqual(Path(self.args.output).read_text(),'keep')
        self.assertEqual(len(self.manifest()['calls']),2)

    def test_shared_budget_counts_corrections_and_prevents_extra_subprocess(self):
        self.config_set(repair_map=True);self.args.max_calls=1
        budget={'used':0};Path(self.args.output).write_text('keep')
        with self.assertRaisesRegex(ValueError,'호출 상한'):self.execute(budget)
        self.assertEqual(budget['used'],1);self.assertEqual(len(self.calls()),1)
        self.assertEqual(Path(self.args.output).read_text(),'keep')

    def test_cli_response_and_format_failures_preserve_existing_output(self):
        for config in [{'fail':'map'},{'fail':'final'},{'oversize':'map'},{'oversize':'final'},
                       {'malformed':True},{'badfinal':True}]:
            with self.subTest(config=config):
                self.config_set(**config);Path(self.args.output).write_text('keep')
                with self.assertRaises(ValueError):self.execute()
                self.assertEqual(Path(self.args.output).read_text(),'keep')
                self.assertEqual(self.manifest()['status'],'error')

    def test_empty_oversized_and_output_input_conflicts_make_no_calls(self):
        for text in ['', 'x'*(1024*1024+1)]:
            self.raw.write_text(text)
            with self.assertRaises(ValueError):self.execute()
        self.args.output=str(self.prompt)
        with self.assertRaises(ValueError):self.execute()
        self.assertFalse(self.calls())

    def test_dry_run_prepares_at_most_three_inputs_and_does_not_publish(self):
        self.args.dry_run=True;self.args.cli='missing-cli';Path(self.args.output).write_text('keep')
        self.assertEqual(self.execute(),0);meta=self.manifest()
        self.assertLessEqual(len(meta['calls']),3);self.assertEqual(meta['calls_used_total'],0)
        self.assertEqual(Path(self.args.output).read_text(),'keep');self.assertFalse(self.calls())

    def test_backup_after_success_and_no_overwrite_guard(self):
        Path(self.args.output).write_text('previous');self.args.overwrite=False
        with self.assertRaises(ValueError):self.execute()
        self.assertFalse(self.calls());self.args.overwrite=True;self.assertEqual(self.execute(),0)
        backups=list((self.root/'runs').glob('*/previous.md'))
        self.assertEqual(backups[0].read_text(),'previous')

    def test_six_tasks_have_at_most_three_maps_no_reducers_and_preserve_sources(self):
        lesson=self.root/'lesson';shutil.copytree(Path(run_lesson1.__file__).parent,lesson,ignore=shutil.ignore_patterns('runs','__pycache__'))
        argv=['run_lesson1.py','--cli',sys.executable,'--cli-arg='+str(self.fake),'--task','all','--overwrite']
        before={p.name:p.read_bytes() for p in (lesson/'raw').glob('*.md')}
        with patch.object(run_lesson1,'LESSON',lesson),patch.object(run_lesson1,'RAW',list((lesson/'raw').glob('*.md'))),patch.object(sys,'argv',argv),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run_lesson1.main(),0)
        manifests=[json.loads(p.read_text()) for p in (lesson/'runs').glob('*/manifest.json')]
        self.assertEqual(len(manifests),6)
        for meta in manifests:
            self.assertLessEqual(meta['initial_map_groups'],3)
            self.assertEqual(len(meta['calls']),meta['initial_map_groups']+1)
            self.assertEqual(meta['selection'],[]);self.assertEqual(meta['omitted_ids'],[])
        self.assertEqual(max(m['calls_used_total'] for m in manifests),len(self.calls()))
        self.assertEqual(before,{p.name:p.read_bytes() for p in (lesson/'raw').glob('*.md')})
        self.assertTrue(any(s['source_kind']=='derived' for c in self.calls() if c['stage']=='map' for s in c['payload']['sources']))

    def test_csv_and_final_link_validation(self):
        self.args.output=str(self.root/'out.csv');Path(self.args.output).write_text('keep');self.config_set(badcsv=True)
        with self.assertRaises(ValueError):self.execute()
        self.assertEqual(Path(self.args.output).read_text(),'keep')
        with self.assertRaises(ValueError):pipeline.validate_final('# T\n[bad][ref]\n[ref]: absent',self.root/'out.md',[self.raw],self.root)
        pipeline.validate_final('# T\n[원문](raw.md)',self.root/'out.md',[self.raw],self.root)


if __name__=='__main__':unittest.main()
