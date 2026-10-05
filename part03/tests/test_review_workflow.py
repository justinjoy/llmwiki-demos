import csv
import io
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import subprocess
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_workflow import ROOT,Store,FIELDS,verify_export_file

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        for f in ['assertions.jsonl','error_candidates.json']:shutil.copy2(ROOT/f,self.root/f)
        (self.root/'review.csv').write_text('id,판정,근거 또는 이유,검토자\n'+''.join(f'{i},pending,,\n' for i in ['F01','F02','F03',*[f'E{x:02}' for x in range(1,7)]]))
        shutil.copytree(ROOT/'raw',self.root/'raw')
        self.store=Store(self.root);self.store.init()
    def tearDown(self):self.temp.cleanup()
    def row(self,ident):return next(r for r in self.store.current() if r['id']==ident)
    def finish(self):
        for r in self.store.current():
            if r['status']!='pending':continue
            status='approved' if r['kind']=='assertion' else 'held' if r['id']=='E04' else 'rejected'
            self.store.decide(r['id'],r['revision'],status,'테스트 검토자','원문 확인을 가정한 테스트 판정')
    def test_cli_show_selects_same_store_as_csv(self):
        original=json.loads(self.row('F03')['payload'])
        self.store.revise('F03',1,'테스트','별도 폴더 후보 구분',dict(original,subject='ledger',object='pay'))
        before=self.store.sheet.read_bytes()
        result=subprocess.run([sys.executable,str(ROOT/'review_workflow.py'),'--root',str(self.root),'show','F03'],capture_output=True,text=True,check=True)
        shown=json.loads(result.stdout)
        with self.store.sheet.open() as f:
            csv_row=next(r for r in csv.DictReader(f) if r['id']=='F03')
        self.assertEqual(str(shown['revision']),csv_row['revision'])
        self.assertEqual(shown['content_sha'],csv_row['content_sha256'])
        self.assertEqual(shown['payload']['subject'],'ledger')
        self.assertEqual(self.store.sheet.read_bytes(),before)

    def test_prefilled_reasons_allow_partial_import_without_false_decisions(self):
        with self.store.sheet.open() as f:rows=list(csv.DictReader(f))
        self.assertTrue(all(r['근거 또는 이유'] and r['판정']=='pending' and not r['검토자'] for r in rows))
        for r in rows:
            if r['id']=='F01':r.update(판정='approved',검토자='실제 검토자')
            if r['id']=='E02':r['근거 또는 이유']='검토자가 작성 중인 근거 초안'
        self.assertEqual(self.store.apply(rows),1)
        self.assertEqual(self.row('F01')['status'],'approved')
        self.assertEqual(self.row('E02')['review_reason'],'')
        self.assertIsNone(self.store.history('E02')[0]['status'])
        with self.store.sheet.open() as f:saved={r['id']:r for r in csv.DictReader(f)}
        self.assertEqual(saved['E02']['근거 또는 이유'],'검토자가 작성 중인 근거 초안')
        original=json.loads(self.row('E02')['payload'])
        self.store.revise('E02',1,'수정자','새 주장',dict(original,claim='새로운 주장'))
        with self.store.sheet.open() as f:updated={r['id']:r for r in csv.DictReader(f)}
        self.assertNotEqual(updated['E02']['근거 또는 이유'],'검토자가 작성 중인 근거 초안')
        self.assertIn('수정된 예문',updated['E02']['근거 또는 이유'])
        with self.assertRaises(ValueError):self.store.export(True)

    def test_prefill_keeps_unsaved_decision_and_user_reason(self):
        with self.store.sheet.open() as f:rows=list(csv.DictReader(f))
        rows[0].update(판정='rejected',검토자='작성 중인 검토자',**{'근거 또는 이유':'직접 작성한 이유'})
        rows[-1]['근거 또는 이유']=''
        with self.store.sheet.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
        self.store.prefill_reasons()
        with self.store.sheet.open() as f:result=list(csv.DictReader(f))
        self.assertEqual(result[0],rows[0])
        self.assertTrue(result[-1]['근거 또는 이유'])
        self.assertTrue(all(r['status']=='pending' for r in self.store.current()))

    def test_initial_pending_and_versioned_csv(self):
        self.assertTrue(all(r['status']=='pending' and r['revision']==1 for r in self.store.current()))
        with self.store.sheet.open() as f:self.assertEqual(next(csv.reader(f)),FIELDS)
        self.assertTrue(list((self.root/'.review/backups').glob('review-*.csv')))
    def test_reject_correct_reapprove_history(self):
        original=json.loads(self.row('F03')['payload']);bad=dict(original,subject='ledger',object='pay')
        self.store.revise('F03',1,'테스트 편집자','잘못된 방향을 검토하는 테스트',bad)
        self.store.decide('F03',2,'rejected','테스트 검토자','ARCH-01 v1 §2 방향이 반대')
        self.store.revise('F03',2,'테스트 편집자','원문대로 pay → ledger로 정정',original)
        self.assertEqual(self.row('F03')['status'],'pending')
        self.store.decide('F03',3,'approved','테스트 재검토자','원문 인용·방향 확인')
        h=self.store.history('F03');self.assertEqual([r['status'] for r in h],[None,'rejected','approved'])
        self.assertEqual(h[2]['changes']['subject'],{'before':'ledger','after':'pay'})
        self.finish();self.assertEqual(self.store.export(True),{'approved':3,'held':1,'rejected':5})
        output=verify_export_file(self.root/'approved.jsonl');self.assertEqual(next(r for r in output if r['assertion_id']=='F03')['candidate_revision'],3)
    def test_reopen_keeps_content_requires_new_decision(self):
        self.store.decide('F01',1,'held','검토자','추가 확인')
        old=self.row('F01');self.store.revise('F01',1,'검토자','추가 근거 확인 후 재검토',reopen=True)
        new=self.row('F01');self.assertEqual(new['content_sha'],old['content_sha']);self.assertEqual(new['revision'],2);self.assertEqual(new['status'],'pending')
    def test_revision_invalidates_approval_immediately(self):
        self.finish();self.store.export(True)
        p=json.loads(self.row('F03')['payload']);p['scope']+=' / 범위 확인'
        self.store.revise('F03',1,'편집자','범위 변경',p)
        self.assertEqual((self.root/'approved.jsonl').read_text(),'')
        with self.assertRaises(ValueError):verify_export_file(self.root/'approved.jsonl')
        with self.assertRaises(ValueError):self.store.export(True)
    def test_stale_csv_even_when_reopened_content_same(self):
        self.finish();old=self.root/'old.csv';shutil.copy2(self.store.sheet,old)
        self.store.revise('F01',1,'검토자','재확인',reopen=True)
        with self.assertRaises(ValueError):self.store.import_csv(old)
        self.assertEqual(self.row('F01')['status'],'pending')
    def test_cannot_replace_decision_in_same_revision(self):
        self.store.decide('F01',1,'rejected','검토자','확인 필요')
        with self.assertRaises(ValueError):self.store.decide('F01',1,'approved','검토자','승인 변경')
        self.assertEqual(self.store.decide('F01',1,'rejected','검토자','확인 필요'),0)
    def test_invalid_change_leaves_history_and_export(self):
        self.finish();self.store.export(True);before=(self.root/'approved.jsonl').read_bytes()
        bad=json.loads(self.row('F01')['payload']);bad['quote']='원문에 없는 문장'
        with self.assertRaises(ValueError):self.store.revise('F01',1,'편집자','오류',bad)
        self.assertEqual(len(self.store.history('F01')),1);self.assertEqual((self.root/'approved.jsonl').read_bytes(),before)
    def test_stale_editor_revision_rejected(self):
        p=json.loads(self.row('F01')['payload']);p['scope']+=' 확인'
        self.store.revise('F01',1,'편집자','범위',p)
        with self.assertRaises(ValueError):self.store.revise('F01',1,'다른 편집자','범위',p)
    def test_error_example_can_be_corrected_to_structured_candidate(self):
        with self.assertRaises(ValueError):self.store.decide('E01',1,'approved','검토자','잘못된 승인')
        self.store.decide('E01',1,'rejected','검토자','방향이 반대')
        p=json.loads(self.row('F03')['payload']);p['assertion_id']='E01'
        self.store.revise('E01',1,'편집자','구조화된 원문 사실로 정정',p,'assertion')
        self.store.decide('E01',2,'approved','검토자','원문 대조 완료')
        self.assertEqual(self.store.history('E01')[0]['kind'],'error_example')
        self.assertEqual(self.row('E01')['kind'],'assertion')
    def test_external_source_change_blocks_consumption_until_sync(self):
        self.finish();self.store.export(True)
        lines=[json.loads(s) for s in (self.root/'assertions.jsonl').read_text().splitlines()];lines[0]['scope']+=' / 새 추출'
        (self.root/'assertions.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in lines))
        with self.assertRaises(ValueError):verify_export_file(self.root/'approved.jsonl')
        self.assertEqual(self.store.sync('LLM 테스트','재추출'),['F01']);self.assertEqual(self.row('F01')['status'],'pending')
    def test_manual_revision_is_not_overwritten_by_unchanged_source(self):
        p=json.loads(self.row('F01')['payload']);p['scope']+=' 직접 확인'
        self.store.revise('F01',1,'편집자','범위',p)
        self.assertEqual(self.store.sync('LLM 테스트','동일 재추출'),[]);self.assertEqual(self.row('F01')['revision'],2)
    def test_history_tables_cannot_be_rewritten(self):
        self.store.decide('F01',1,'rejected','검토자','이유')
        for table in ['revisions','decisions']:
            with self.assertRaises(sqlite3.IntegrityError):
                with self.store.connect() as con:con.execute(f'DELETE FROM {table}')
    def test_legacy_csv_cannot_silently_approve(self):
        p=self.root/'legacy.csv';p.write_text('id,판정,근거 또는 이유,검토자\nF01,approved,이유,검토자\n')
        with self.assertRaises(ValueError):self.store.import_csv(p)
    def test_atomic_review_batch_rejects_stale_row(self):
        with self.store.sheet.open() as f:rows=list(csv.DictReader(f))
        for r in rows:
            if r['id']=='F01':r.update(판정='approved',검토자='검토자',**{'근거 또는 이유':'원문 확인'})
            if r['id']=='F02':r['revision']='99'
        with self.assertRaises(ValueError):self.store.apply(rows)
        self.assertEqual(self.row('F01')['status'],'pending')
    def test_partial_review_is_saved_without_publishing(self):
        self.store.decide('F01',1,'approved','검토자','원문 확인')
        with self.assertRaises(ValueError):self.store.export(True)
        self.assertEqual(self.row('F01')['status'],'approved');self.assertEqual((self.root/'approved.jsonl').read_text(),'')
    def test_export_hash_tampering_detected(self):
        self.finish();self.store.export(True)
        p=self.root/'approved.jsonl';p.write_text(p.read_text()+'\n')
        with self.assertRaises(ValueError):verify_export_file(p)
    def test_detached_managed_export_is_rejected(self):
        self.finish();self.store.export(True)
        folder=self.root/'detached';folder.mkdir();shutil.copy2(self.root/'approved.jsonl',folder/'approved.jsonl')
        with self.assertRaises(ValueError):verify_export_file(folder/'approved.jsonl')

if __name__=='__main__':unittest.main()
