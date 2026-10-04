#!/usr/bin/env python3
"""Loopback-only web UI for the same natural-language assistant as ask.py."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
from urllib.parse import urlsplit
from llmwiki.agent import Assistant,CLIModel
ROOT=Path(__file__).resolve().parent

class App:
    def __init__(self,bot):
        self.bot=bot;self.token=secrets.token_urlsafe(32);self.jobs={};self.lock=threading.Lock()
        self.pool=ThreadPoolExecutor(max_workers=1)
    def submit(self,question,snapshot,history):
        if not isinstance(question,str) or not 1<=len(question.strip())<=4000:raise ValueError('질문은 1~4000자로 입력하세요.')
        if snapshot not in self.bot.graph.snapshots:raise ValueError('스냅샷 오류')
        if not isinstance(history,list) or len(history)>3 or len(json.dumps(history,ensure_ascii=False))>18000:raise ValueError('대화 이력이 너무 큽니다. 새 대화로 시작하세요.')
        with self.lock:
            if sum(j['status'] in ('queued','running') for j in self.jobs.values())>=2:raise ValueError('처리 중인 질문이 있습니다. 완료 후 다시 시도하세요.')
            if len(self.jobs)>=40:
                for key in list(self.jobs):
                    if self.jobs[key]['status'] not in ('queued','running'):del self.jobs[key];break
            ident=secrets.token_hex(12);self.jobs[ident]={'status':'queued','events':[]}
        self.pool.submit(self.run,ident,question,snapshot,history)
        return ident
    def run(self,ident,question,snapshot,history):
        def event(text):
            with self.lock:self.jobs[ident]['events'].append(text)
        with self.lock:self.jobs[ident]['status']='running'
        try:
            result=self.bot.ask(question,snapshot,history,event)
            with self.lock:self.jobs[ident].update(status='success',result=result)
        except Exception as exc:
            with self.lock:self.jobs[ident].update(status='error',message=str(exc))


def handler_for(app):
    class Handler(BaseHTTPRequestHandler):
        def allowed(self):
            host=self.headers.get('Host','');port=self.server.server_port
            if host not in {f'127.0.0.1:{port}',f'localhost:{port}'}:return False
            origin=self.headers.get('Origin')
            return origin is None or origin in {f'http://127.0.0.1:{port}',f'http://localhost:{port}'}
        def send(self,code,value,kind='application/json; charset=utf-8'):
            data=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False).encode()
            self.send_response(code);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers();self.wfile.write(data)
        def do_GET(self):
            if not self.allowed():return self.send(403,{'error':'로컬 주소에서 접속하세요.'})
            path=urlsplit(self.path).path
            files={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8')}
            if path in files:
                f,t=files[path];return self.send(200,(ROOT/'web'/f).read_bytes(),t)
            if path=='/api/config':return self.send(200,{'token':app.token,'engine':'PyreWire 1.1.2','cli':app.bot.model.cli,'documents':len(app.bot.corpus.docs)})
            if path.startswith('/api/jobs/'):
                if self.headers.get('X-Local-Token')!=app.token:return self.send(403,{'error':'세션 토큰 오류'})
                with app.lock:
                    job=app.jobs.get(path.rsplit('/',1)[1]);value=json.loads(json.dumps(job)) if job else None
                return self.send(200,value) if value else self.send(404,{'error':'질문 기록이 없습니다.'})
            self.send(404,{'error':'경로가 없습니다.'})
        def do_POST(self):
            if not self.allowed() or self.headers.get('X-Local-Token')!=app.token:return self.send(403,{'error':'로컬 세션 토큰이 필요합니다.'})
            if self.path!='/api/ask':return self.send(404,{'error':'경로가 없습니다.'})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=65536:raise ValueError('요청 크기 오류')
                data=json.loads(self.rfile.read(length))
                if not isinstance(data,dict):raise ValueError('JSON 객체가 필요합니다.')
                ident=app.submit(data.get('question'),data.get('snapshot','S1b'),data.get('history',[]))
            except (ValueError,TypeError) as exc:return self.send(400,{'error':str(exc)})
            self.send(202,{'job_id':ident})
    return Handler


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',type=int,default=8765)
    p.add_argument('--cli',default='agy');p.add_argument('--cli-arg',action='append',default=[])
    p.add_argument('--mode',choices=['auto','print','codex'],default='auto');p.add_argument('--timeout',type=float,default=180)
    a=p.parse_args()
    if not 1<=a.port<=65535 or a.timeout<=0:p.error('port/timeout 값을 확인하세요.')
    bot=Assistant(ROOT/'data',ROOT/'runs',CLIModel(a.cli,a.cli_arg,a.timeout,a.mode))
    app=App(bot);server=ThreadingHTTPServer(('127.0.0.1',a.port),handler_for(app))
    print(f'LLMWiki + PyreWire: http://127.0.0.1:{a.port}  (LLM: {a.cli})',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close();app.pool.shutdown(wait=True,cancel_futures=True)
if __name__=='__main__':main()
