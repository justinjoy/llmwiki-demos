#!/usr/bin/env python3
"""Natural-language LLMWiki questions, one-shot or interactive chat."""
import argparse
import json
from pathlib import Path
import sys
from llmwiki.agent import Assistant,CLIModel,render_answer
ROOT=Path(__file__).resolve().parent

def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('question',nargs='?')
    p.add_argument('--chat',action='store_true')
    p.add_argument('--cli',default='agy');p.add_argument('--cli-arg',action='append',default=[])
    p.add_argument('--mode',choices=['auto','print','codex'],default='auto')
    p.add_argument('--timeout',type=float,default=180)
    p.add_argument('--snapshot',choices=['S1','S1b','S2','S3'],default='S1b')
    return p

def main():
    p=parser();a=p.parse_args()
    if not a.chat and not a.question:p.error('질문 또는 --chat을 지정하세요.')
    if a.timeout<=0:p.error('--timeout은 양수여야 합니다.')
    bot=Assistant(ROOT/'data',ROOT/'runs',CLIModel(a.cli,a.cli_arg,a.timeout,a.mode))
    history=[];question=a.question
    while True:
        if not question:
            try:question=input('\n질문 (/quit 종료, /reset 새 대화): ').strip()
            except (EOFError,KeyboardInterrupt):break
        if question=='/quit':break
        if question=='/reset':history=[];question=None;continue
        if not question:continue
        try:
            result=bot.ask(question,a.snapshot,history,lambda s:print(s,file=sys.stderr))
            print(render_answer(result));print('실행 기록:',ROOT/'runs'/result['run_id'])
            history.append({'question':question[:1000],'answer':json.dumps(result['answer'],ensure_ascii=False)[:3500]})
        except (ValueError,RuntimeError) as exc:
            print(str(exc),file=sys.stderr)
            if not a.chat:return 1
        if not a.chat:break
        question=None
    return 0
if __name__=='__main__':sys.exit(main())
