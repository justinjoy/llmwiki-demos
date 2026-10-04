import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llmwiki.agent import Assistant
from llmwiki.corpus import Corpus
from llmwiki.graph import Graph
ROOT=Path(__file__).resolve().parents[1]

class ScriptedModel:
    def __init__(self,responses):self.responses=iter(responses);self.states=[]
    def complete(self,state,run_dir,index):self.states.append(copy.deepcopy(state));return next(self.responses)

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.corpus=Corpus(ROOT/'data');cls.graph=Graph(cls.corpus)
    def test_real_graph_snapshots(self):
        for sid,services in [('S1',['order','pay','shop']),('S1b',['notify','order','pay','shop']),('S2',['order','pay','shop']),('S3',['order','shop'])]:
            with self.subTest(sid=sid):
                r=self.graph.query('upstream','ledger',sid)
                self.assertEqual([r[0] for r in r['rows']],services);self.assertEqual(r['engine_version'],'1.1.2')
    def test_direction_and_path(self):
        r=self.graph.query('downstream','order');self.assertEqual(r['rows'],[['order','ledger'],['order','pay']])
        self.assertEqual(self.graph.query('path','notify',target='ledger')['paths'][0]['assertion_ids'],['F04','F02','F03'])
        self.assertEqual(self.graph.query('path','ledger',target='shop')['status'],'empty')
    def test_nonservice_and_unknown_snapshot(self):
        for args in [('upstream','ledger-db','S1'),('upstream','pay','missing')]:
            with self.assertRaises(ValueError):self.graph.query(*args)
    def test_raw_search_and_quotes(self):
        hit=self.corpus.search('타임아웃 대사','raw')['hits'][0]
        section=self.corpus.read(hit['doc_id'],hit['section'])[0]
        self.assertIn(section['quote'],(ROOT/'data'/section['path']).read_text())
        self.assertEqual(self.corpus.docs['ARCH-01:v2']['status'],'draft')
        self.assertEqual(self.corpus.search('zzzznothing')['status'],'empty')
    def test_no_arbitrary_files(self):
        with self.assertRaises(ValueError):self.corpus.read('../../README.md')
    def test_pending_fact_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'data';shutil.copytree(ROOT/'data',p)
            f=p/'snapshots/S1b.json';d=json.loads(f.read_text());d['assertions'][0]['review_status']='pending';f.write_text(json.dumps(d))
            with self.assertRaises(ValueError):Graph(Corpus(p))
    def test_real_tools_and_history(self):
        model=ScriptedModel([{'type':'tools','calls':[{'tool':'read_document','arguments':{'doc_id':'ARCH-01:v1','section':'§3'}}]},
          {'type':'answer','claims':[{'text':'결제 서비스 운영 팀은 결제정산팀입니다.','kind':'fact','citations':['E1']}],'unknowns':['현재 당직자 이름은 없습니다.']}])
        with tempfile.TemporaryDirectory() as temp:
            bot=Assistant(ROOT/'data',temp,model);result=bot.ask('그 팀은?',history=[{'question':'결제 담당 팀?','answer':{}}])
            self.assertEqual(result['status'],'success');self.assertEqual(len(result['tool_calls']),1)
            self.assertEqual(model.states[0]['previous_conversation'][0]['question'],'결제 담당 팀?')
            self.assertEqual(result['evidence']['E1']['doc_id'],'ARCH-01:v1')
            self.assertTrue((Path(temp)/result['run_id']/'answer.md').exists())
    def test_fabricated_citation_never_published(self):
        bad={'type':'answer','claims':[{'text':'없는 사실','kind':'fact','citations':['E999']}],'unknowns':[]}
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(RuntimeError):Assistant(ROOT/'data',temp,ScriptedModel([bad,bad,bad])).ask('질문')
            self.assertFalse(list(Path(temp).glob('*/answer.json')))
            self.assertEqual(json.loads(next(Path(temp).glob('*/run.json')).read_text())['status'],'error')
    def test_wiki_only_not_primary_proof(self):
        with self.assertRaises(ValueError):Assistant.validate_answer({'claims':[{'text':'주장','kind':'fact','citations':['E1']}],'unknowns':[]},{'E1':{'kind':'wiki'}})
    def test_unsupported_question_can_abstain(self):
        model=ScriptedModel([{'type':'answer','claims':[],'unknowns':['자료에 날씨 정보가 없습니다.'],'follow_up':'서비스 문서 관련 질문을 입력하세요.'}])
        with tempfile.TemporaryDirectory() as temp:self.assertEqual(Assistant(ROOT/'data',temp,model).ask('오늘 날씨?')['answer']['claims'],[])
    def test_budget_and_no_execution_tool(self):
        illegal={'type':'tools','calls':[{'tool':'execute_shell','arguments':{'command':'ignored'}}]}
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(RuntimeError):Assistant(ROOT/'data',temp,ScriptedModel([illegal]*3)).ask('명령')
    def test_original_data_preserved(self):
        manifest=json.loads((ROOT/'data/manifest.json').read_text())
        for name,sha in manifest['files'].items():self.assertEqual(hashlib.sha256((ROOT/'data'/name).read_bytes()).hexdigest(),sha,name)

class HTTPTests(unittest.TestCase):
    def test_browser_api_end_to_end(self):
        from http.server import ThreadingHTTPServer
        from urllib.request import Request,urlopen
        from urllib.error import HTTPError
        import threading
        from serve import App,handler_for
        model=ScriptedModel([{'type':'answer','claims':[],'unknowns':['제공 자료에 정보가 없습니다.']}]);model.cli='test-model'
        with tempfile.TemporaryDirectory() as temp:
            app=App(Assistant(ROOT/'data',temp,model));server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(app))
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            base=f'http://127.0.0.1:{server.server_port}'
            try:
                with urlopen(base+'/') as r:self.assertIn('자연어 질문',r.read().decode())
                with urlopen(base+'/api/config') as r:config=json.load(r)
                request=Request(base+'/api/ask',data=json.dumps({'question':'자료에 없는 질문'}).encode(),headers={'Content-Type':'application/json'})
                with self.assertRaises(HTTPError) as e:urlopen(request)
                self.assertEqual(e.exception.code,403);e.exception.close()
                request.add_header('X-Local-Token',config['token'])
                with urlopen(request) as r:job=json.load(r)['job_id']
                app.pool.shutdown(wait=True)
                with urlopen(Request(base+'/api/jobs/'+job,headers={'X-Local-Token':config['token']})) as r:
                    result=json.load(r);self.assertEqual(result['status'],'success');self.assertTrue(result['result']['answer']['unknowns'])
                with self.assertRaises(HTTPError) as e:urlopen(base+'/data/raw/ARCH-01_v1.md')
                self.assertEqual(e.exception.code,404);e.exception.close()
            finally:server.shutdown();server.server_close();app.pool.shutdown(wait=True)

if __name__=='__main__':unittest.main()
