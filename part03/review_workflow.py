"""Versioned human review: append-only revisions/decisions, CSV review, audited export."""
import argparse
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
from validate_assertions import validate

ROOT=Path(__file__).resolve().parent
FIELDS=['id','revision','content_sha256','판정','근거 또는 이유','검토자']
STATES={'pending','approved','rejected','held'}

def encoded(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def digest(value):return hashlib.sha256(encoded(value).encode()).hexdigest()
def stamp():return datetime.now(timezone.utc).isoformat()
def required(text,label):
    if not isinstance(text,str) or not text.strip() or 'TODO' in text:raise ValueError(label+'를 실제 값으로 작성하세요.')
    return text.strip()
def atomic(path,text):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix='.review-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8',newline='') as f:f.write(text)
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)

def validate_candidate(root,ident,kind,payload):
    if not isinstance(payload,dict):raise ValueError('후보는 JSON 객체여야 합니다.')
    payload=dict(payload)
    if kind=='assertion':
        if payload.get('assertion_id')!=ident:raise ValueError('assertion_id는 기존 후보 ID를 유지하세요.')
        payload['review_status']='pending';payload['reviewer']=''
        for key in ('review_reason','candidate_revision','reviewed_sha256'):payload.pop(key,None)
        # Validation uses the selected lesson directory, including in isolated tests.
        import validate_assertions as checks
        previous=checks.ROOT;checks.ROOT=Path(root)
        try:
            with tempfile.TemporaryDirectory() as temp:
                p=Path(temp)/'candidate.jsonl';p.write_text(encoded(payload)+'\n',encoding='utf-8')
                errors=validate(p,'pending')
        finally:checks.ROOT=previous
        if errors:raise ValueError('후보 검사 실패: '+'; '.join(errors))
    elif kind=='error_example':
        if payload.get('id')!=ident:raise ValueError('id는 기존 후보 ID를 유지하세요.')
        required(payload.get('claim'),'후보 주장')
    else:raise ValueError('kind는 assertion 또는 error_example입니다.')
    return payload

def suggested_reason(kind,payload):
    """Reading aid only; never records a human decision."""
    if kind=='assertion':
        return (f"{payload.get('source_id','')} {payload.get('version','')} {payload.get('section','')}: "
                f"원문 인용: {payload.get('quote','')} / "
                f"검토할 후보: {payload.get('subject','')} {payload.get('predicate','')} {payload.get('object','')}. "
                "방향·범위·문서 적용 상태를 대조하세요.")
    references={
        'ledger depends_on pay':'ARCH-01 v1 §2: 원문은 pay가 ledger를 호출한다고 설명합니다. 후보의 호출 방향을 대조하세요.',
        'pay 담당 팀 Platform':'ARCH-01 v1 §3: pay 운영 담당은 결제정산팀입니다. 후보의 담당 팀을 대조하세요.',
        'shop depends_on ledger 직접 호출':'ARCH-01 v1 §1·§2: shop → order → pay → ledger 경로입니다. 직접 호출인지 간접 경로인지 구분하세요.',
        'pay 원장 호출 제거 완료':'ARCH-01 v2 §1·§2: 검토 중인 설계안이며 운영 반영을 확정하지 않았습니다. 승인·배포 여부를 확인하세요.',
        'ledger-db = ledger Service':'GLOSS-01 v1 §1: ledger-db는 DataStore입니다. ledger 서비스와 유형을 구분하세요.',
        'payment와 pay 별도 서비스':'GLOSS-01 v1 §1: payment는 pay의 별칭입니다. 별개 서비스인지 대조하세요.',
    }
    return references.get(payload.get('claim'),'수정된 예문입니다. 원문 위치와 현재 주장에 맞는 판단 근거를 작성하세요.')

class Store:
    def __init__(self,root=ROOT,example=False):
        self.root=Path(root).resolve();self.output=self.root/'example_output' if example else self.root
        self.db=self.output/'.review/state.sqlite3';self.sheet=self.output/'review.csv'
        self.example=example
    @contextmanager
    def connect(self):
        if not self.db.exists():raise ValueError('먼저 python3 review_workflow.py init을 실행하세요.')
        con=sqlite3.connect(self.db,timeout=15);con.row_factory=sqlite3.Row
        con.execute('PRAGMA foreign_keys=ON')
        try:
            with con:yield con
        finally:con.close()
    def sources(self):
        result={}
        for line in (self.root/'assertions.jsonl').read_text(encoding='utf-8-sig').splitlines():
            if not line.strip():continue
            p=json.loads(line);ident=p.get('assertion_id')
            if not isinstance(ident,str) or not ident or ident in result:raise ValueError('중복·빈 추출 ID')
            result[ident]=('assertion',validate_candidate(self.root,ident,'assertion',p))
        for p in json.loads((self.root/'error_candidates.json').read_text()):
            ident=p.get('id')
            if not isinstance(ident,str) or not ident or ident in result:raise ValueError('중복·빈 오류 예문 ID')
            result[ident]=('error_example',validate_candidate(self.root,ident,'error_example',p))
        if not result:raise ValueError('후보가 없습니다.')
        return result
    def invalidate(self,reason):
        # Clear the consumption file BEFORE changing the database: a crash fails closed.
        folder=self.output/'.review/backups';folder.mkdir(parents=True,exist_ok=True)
        previous=self.output/'approved.jsonl'
        if previous.exists() and previous.stat().st_size:
            backup=folder/f'approved-{datetime.now().strftime("%Y%m%d-%H%M%S-%f")}.jsonl'
            shutil.copy2(previous,backup)
        atomic(previous,'')
        atomic(self.output/'approved.meta.json',json.dumps({'status':'invalidated','example':self.example,'reason':reason,'at':stamp()},ensure_ascii=False,indent=2)+'\n')
    def init(self):
        sources=self.sources()
        if self.db.exists():return False
        self.db.parent.mkdir(parents=True,exist_ok=True)
        con=sqlite3.connect(self.db);con.row_factory=sqlite3.Row
        try:
            con.executescript('''
            CREATE TABLE heads(id TEXT PRIMARY KEY, revision INTEGER NOT NULL, source_sha TEXT NOT NULL);
            CREATE TABLE revisions(id TEXT NOT NULL, revision INTEGER NOT NULL, kind TEXT NOT NULL,
              payload TEXT NOT NULL, content_sha TEXT NOT NULL, action TEXT NOT NULL,
              actor TEXT NOT NULL, reason TEXT NOT NULL, at TEXT NOT NULL, PRIMARY KEY(id,revision));
            CREATE TABLE decisions(id TEXT NOT NULL, revision INTEGER NOT NULL, status TEXT NOT NULL,
              reviewer TEXT NOT NULL, reason TEXT NOT NULL, at TEXT NOT NULL, PRIMARY KEY(id,revision),
              FOREIGN KEY(id,revision) REFERENCES revisions(id,revision));
            CREATE TRIGGER immutable_revision_update BEFORE UPDATE ON revisions BEGIN SELECT RAISE(ABORT,'revision immutable'); END;
            CREATE TRIGGER immutable_revision_delete BEFORE DELETE ON revisions BEGIN SELECT RAISE(ABORT,'revision immutable'); END;
            CREATE TRIGGER immutable_decision_update BEFORE UPDATE ON decisions BEGIN SELECT RAISE(ABORT,'decision immutable'); END;
            CREATE TRIGGER immutable_decision_delete BEFORE DELETE ON decisions BEGIN SELECT RAISE(ABORT,'decision immutable'); END;
            ''')
            for ident,(kind,payload) in sources.items():
                sha=digest(payload)
                con.execute('INSERT INTO heads VALUES(?,?,?)',(ident,1,sha))
                con.execute('INSERT INTO revisions VALUES(?,?,?,?,?,?,?,?,?)',(ident,1,kind,encoded(payload),sha,'created','시스템 초기화(사람 검토 아님)','현재 추출·오류 예문을 최초 후보로 등록',stamp()))
            self.invalidate('검토 저장소 초기화. 후보별 최신 버전을 검토한 뒤 내보내세요.')
            con.commit()
        finally:con.close()
        self.worksheet();return True
    @staticmethod
    def rows(con):
        return con.execute('''SELECT r.*,h.source_sha,COALESCE(d.status,'pending') AS status,
          COALESCE(d.reviewer,'') AS reviewer,COALESCE(d.reason,'') AS review_reason,d.at AS reviewed_at
          FROM heads h JOIN revisions r ON h.id=r.id AND h.revision=r.revision
          LEFT JOIN decisions d ON r.id=d.id AND r.revision=d.revision ORDER BY r.id''').fetchall()
    def current(self):
        with self.connect() as con:return [dict(r) for r in self.rows(con)]
    def check_sources(self,con):
        sources=self.sources();heads={r['id']:r for r in con.execute('SELECT * FROM heads')}
        if set(heads)!=set(sources) or any(heads[i]['source_sha']!=digest(p) for i,(_,p) in sources.items()):
            raise ValueError('추출 파일이 검토 기준과 달라졌습니다. review_workflow.py sync --actor 이름 --reason 이유 를 실행하세요.')
    def worksheet(self,drafts=None):
        # Review CSV is a working copy, never the historical system of record.
        previous={}
        if self.sheet.exists():
            with self.sheet.open(encoding='utf-8-sig',newline='') as f:
                reader=csv.DictReader(f)
                if reader.fieldnames==FIELDS:
                    previous={(r['id'],r['revision'],r['content_sha256']):r.get('근거 또는 이유','') for r in reader}
        previous.update(drafts or {})
        buf=io.StringIO(newline='');writer=csv.writer(buf,lineterminator="\n");writer.writerow(FIELDS)
        for r in self.current():
            reason=r['review_reason']
            if r['status']=='pending':
                reason=previous.get((r['id'],str(r['revision']),r['content_sha'])) or suggested_reason(r['kind'],json.loads(r['payload']))
            writer.writerow([r['id'],r['revision'],r['content_sha'],r['status'],reason,r['reviewer']])
        text=buf.getvalue()
        if self.sheet.exists() and self.sheet.read_text(encoding='utf-8-sig')!=text:
            folder=self.output/'.review/backups';folder.mkdir(parents=True,exist_ok=True)
            shutil.copy2(self.sheet,folder/f'review-{datetime.now().strftime("%Y%m%d-%H%M%S-%f")}.csv')
        atomic(self.sheet,text)
        atomic(self.output/'review_history.json',json.dumps(self.history(),ensure_ascii=False,indent=2)+'\n')
        return self.sheet
    def revise(self,ident,expected,actor,reason,payload=None,kind=None,reopen=False):
        actor=required(actor,'수정자');reason=required(reason,'수정·재검토 이유')
        with self.connect() as con:
            con.execute('BEGIN IMMEDIATE');self.check_sources(con)
            rows={r['id']:r for r in self.rows(con)}
            if ident not in rows:raise ValueError('알 수 없는 후보 ID')
            old=rows[ident]
            if old['revision']!=expected:raise ValueError('후보 버전이 변경됐습니다. show/list로 최신 버전을 확인하세요.')
            if reopen:
                if old['status']=='pending':raise ValueError('이미 검토 대기 중입니다.')
                kind=old['kind'];payload=json.loads(old['payload'])
            else:
                kind=kind or old['kind'];payload=validate_candidate(self.root,ident,kind,payload)
                if kind==old['kind'] and digest(payload)==old['content_sha']:raise ValueError('내용 변경이 없습니다. 판정만 재검토하려면 reopen을 사용하세요.')
            new=expected+1
            self.invalidate(f'{ident} r{new} 재검토 필요')
            con.execute('INSERT INTO revisions VALUES(?,?,?,?,?,?,?,?,?)',(ident,new,kind,encoded(payload),digest(payload),'reopened' if reopen else 'revised',actor,reason,stamp()))
            con.execute('UPDATE heads SET revision=? WHERE id=?',(new,ident))
        self.worksheet();return new
    def sync(self,actor,reason):
        actor=required(actor,'등록자');reason=required(reason,'등록 이유');sources=self.sources();changed=[]
        with self.connect() as con:
            con.execute('BEGIN IMMEDIATE');old={r['id']:r for r in self.rows(con)}
            missing=set(old)-set(sources)
            if missing:raise ValueError('기존 ID를 추출 파일에서 삭제할 수 없습니다. 복원 후 반려·보류하세요: '+','.join(sorted(missing)))
            for ident,(kind,payload) in sources.items():
                previous=old.get(ident);sha=digest(payload)
                if previous and previous['source_sha']==sha:continue
                revision=previous['revision']+1 if previous else 1
                changed.append((ident,revision,kind,payload,sha))
            if changed:self.invalidate('추출 후보 변경. 최신 버전 재검토 필요')
            for ident,revision,kind,payload,sha in changed:
                con.execute('INSERT INTO revisions VALUES(?,?,?,?,?,?,?,?,?)',(ident,revision,kind,encoded(payload),sha,'source_updated',actor,reason,stamp()))
                con.execute('INSERT INTO heads VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,source_sha=excluded.source_sha',(ident,revision,sha))
        if changed:self.worksheet()
        return [r[0] for r in changed]
    def apply(self,reviews):
        with self.connect() as con:
            con.execute('BEGIN IMMEDIATE');self.check_sources(con)
            current={r['id']:r for r in self.rows(con)};seen=set();planned=[];drafts={}
            for review in reviews:
                ident=review['id'];status=review['판정']
                if ident in seen or ident not in current:raise ValueError('중복 또는 알 수 없는 ID: '+ident)
                seen.add(ident);r=current[ident]
                if str(r['revision'])!=str(review['revision']) or r['content_sha']!=review['content_sha256']:raise ValueError(f'{ident}: 이전 버전의 판정입니다. 최신 review.csv를 사용하세요.')
                if status not in STATES:raise ValueError('판정은 pending/approved/rejected/held입니다.')
                reviewer=review['검토자'].strip();reason=review['근거 또는 이유'].strip()
                if status=='pending':
                    if r['status']!='pending':raise ValueError(f'{ident}: 기존 판정을 지우려면 reopen이 필요합니다.')
                    if reviewer:raise ValueError(f'{ident}: pending에는 검토자를 비워 두세요. 근거 초안은 남겨도 됩니다.')
                    drafts[(ident,str(r['revision']),r['content_sha'])]=reason
                    continue
                reviewer=required(reviewer,'검토자');reason=required(reason,'판정 근거')
                if r['status']!='pending':
                    if (status,reviewer,reason)==(r['status'],r['reviewer'],r['review_reason']):continue
                    raise ValueError(f'{ident}: 이미 판정됐습니다. 수정 또는 reopen 후 재검토하세요.')
                if status=='approved':
                    if r['kind']!='assertion':raise ValueError(f'{ident}: 오류 예문은 직접 승인할 수 없습니다. 구조화된 assertion으로 수정·재검토하세요.')
                    p=json.loads(r['payload']);validate_candidate(self.root,ident,'assertion',p)
                    if p['document_status']!='approved':raise ValueError(f'{ident}: 운영 승인 문서가 아닙니다.')
                planned.append((ident,r['revision'],status,reviewer,reason,stamp()))
            if planned:self.invalidate('검토 판정 변경. 최신 결과를 다시 내보내세요.')
            con.executemany('INSERT INTO decisions VALUES(?,?,?,?,?,?)',planned)
        self.worksheet(drafts);return len(planned)
    def import_csv(self,path=None):
        with Path(path or self.sheet).open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f)
            if reader.fieldnames!=FIELDS:raise ValueError('버전·해시가 있는 검토 CSV가 필요합니다. init/worksheet로 생성하세요.')
            rows=list(reader)
            if any(None in r or any(v is None for v in r.values()) for r in rows):raise ValueError('CSV 열 수 오류')
            rows=[{k:v.strip() for k,v in r.items()} for r in rows]
        if {r['id'] for r in rows}!={r['id'] for r in self.current()}:raise ValueError('검토 CSV에 모든 후보 ID가 있어야 합니다.')
        return self.apply(rows)
    def decide(self,ident,revision,status,reviewer,reason):
        rows={r['id']:r for r in self.current()}
        if ident not in rows:raise ValueError('알 수 없는 ID')
        return self.apply([dict(zip(FIELDS,[ident,str(revision),rows[ident]['content_sha'],status,reason,reviewer]))])
    def history(self,ident=None):
        with self.connect() as con:
            query='''SELECT r.*,d.status,d.reviewer,d.reason AS review_reason,d.at AS reviewed_at
             FROM revisions r LEFT JOIN decisions d ON r.id=d.id AND r.revision=d.revision'''
            rows=con.execute(query+(' WHERE r.id=?' if ident else '')+' ORDER BY r.id,r.revision',(ident,) if ident else ()).fetchall()
        result=[];previous={}
        for row in rows:
            r=dict(row);r['payload']=json.loads(r['payload']);before=previous.get(r['id'],{})
            r['changes']={k:{'before':before.get(k),'after':r['payload'].get(k)} for k in before.keys()|r['payload'].keys() if before.get(k)!=r['payload'].get(k)}
            previous[r['id']]=r['payload'];result.append(r)
        if ident and not result:raise ValueError('알 수 없는 ID')
        return result
    def export(self,overwrite=False):
        with self.connect() as con:
            con.execute('BEGIN IMMEDIATE');self.check_sources(con);rows=self.rows(con)
            pending=[r['id'] for r in rows if r['status']=='pending']
            if pending:raise ValueError('재검토가 남아 있습니다: '+', '.join(pending))
            if not overwrite and any((self.output/f).exists() for f in ['approved.jsonl','held.json','rejected.json']):raise ValueError('--overwrite로 기존 결과를 백업 후 내보내세요.')
            approved=[];held=[];rejected=[]
            for r in rows:
                p=json.loads(r['payload'])
                if r['status']=='approved':
                    validate_candidate(self.root,r['id'],r['kind'],p)
                    if p['document_status']!='approved':raise ValueError('승인 문서가 아닙니다.')
                    p.update(review_status='approved',reviewer=r['reviewer'],review_reason=r['review_reason'],candidate_revision=r['revision'],reviewed_sha256=r['content_sha'])
                    approved.append(p)
                else:
                    target=held if r['status']=='held' else rejected
                    target.append({'id':r['id'],'revision':r['revision'],'content_sha256':r['content_sha'],'candidate':p,'review_status':r['status'],'reviewer':r['reviewer'],'reason':r['review_reason']})
            self.invalidate('승인 파일 내보내기 진행 중')
            for name,items in [('held.json',held),('rejected.json',rejected)]:atomic(self.output/name,json.dumps(items,ensure_ascii=False,indent=2)+'\n')
            history=self.history();atomic(self.output/'review_history.json',json.dumps(history,ensure_ascii=False,indent=2)+'\n')
            text=''.join(encoded(p)+'\n' for p in approved);atomic(self.output/'approved.jsonl',text)
            metadata={'status':'current','example':self.example,'exported_at':stamp(),'sha256':hashlib.sha256(text.encode()).hexdigest(),
                'heads':{r['id']:{'revision':r['revision'],'sha256':r['content_sha'],'status':r['status']} for r in rows}}
            atomic(self.output/'approved.meta.json',json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
        return {'approved':len(approved),'held':len(held),'rejected':len(rejected)}

def verify_export_file(path):
    path=Path(path).resolve();meta=path.with_name('approved.meta.json');db=path.parent/'.review/state.sqlite3'
    content=path.read_bytes()
    rows=[json.loads(line) for line in content.decode('utf-8').splitlines() if line.strip()]
    managed=db.exists() or meta.exists() or any('candidate_revision' in r for r in rows)
    if not managed:return rows  # Separately supplied unversioned approved input.
    if not db.exists() or not meta.exists():raise ValueError('버전 관리된 승인 파일은 검토 DB·메타데이터와 함께 사용하세요.')
    m=json.loads(meta.read_text());store=Store(path.parent.parent if m.get('example') else path.parent,bool(m.get('example')))
    with store.connect() as con:
        store.check_sources(con);current=store.rows(con)
        heads={r['id']:{'revision':r['revision'],'sha256':r['content_sha'],'status':r['status']} for r in current}
        if m.get('status')!='current' or m.get('heads')!=heads or m.get('sha256')!=hashlib.sha256(content).hexdigest():raise ValueError('오래되었거나 변경된 승인 파일입니다. 재검토 후 export_review.py를 실행하세요.')
        for r in current:
            if r['status']=='approved':validate_candidate(store.root,r['id'],r['kind'],json.loads(r['payload']))
    return rows

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT,help='review.csv와 .review 저장소가 있는 실습 폴더 (기본: part03)')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('init');sub.add_parser('list');sub.add_parser('worksheet')
    show=sub.add_parser('show');show.add_argument('id');show.add_argument('--output',type=Path)
    hist=sub.add_parser('history');hist.add_argument('id',nargs='?');hist.add_argument('--output',type=Path)
    sync=sub.add_parser('sync');sync.add_argument('--actor',required=True);sync.add_argument('--reason',required=True)
    for name in ('revise','reopen'):
        a=sub.add_parser(name);a.add_argument('id');a.add_argument('--revision',type=int,required=True);a.add_argument('--actor',required=True);a.add_argument('--reason',required=True)
        if name=='revise':a.add_argument('--file',type=Path,required=True);a.add_argument('--kind',choices=['assertion','error_example'])
    a=sub.add_parser('decide');a.add_argument('id');a.add_argument('--revision',type=int,required=True);a.add_argument('--status',choices=['approved','held','rejected'],required=True);a.add_argument('--reviewer',required=True);a.add_argument('--reason',required=True)
    a=sub.add_parser('import-review');a.add_argument('--file',type=Path)
    args=p.parse_args();store=Store(args.root)
    try:
        if args.command=='init':print('등록 완료. review.csv에 최신 버전의 판정을 기록하세요.' if store.init() else '이미 초기화됐습니다. 기존 후보와 이력을 유지합니다.')
        elif args.command=='list':
            print('후보ID', '후보버전', '후보종류', '검토상태', '검토자', '판정이유', sep='\t')
            for r in store.current():print(r['id'],f"r{r['revision']}",r['kind'],r['status'],r['reviewer'],r['review_reason'],sep='\t')
            print('rN=후보의 수정 버전 (원문 v1/v2와 별개). assertion=구조화된 사실 후보, error_example=교육용 오류 검토 예문.')
            print('pending=미검토, approved=승인, rejected=반려, held=보류. 빈 검토자·이유는 아직 판정하지 않았다는 뜻입니다.')
            print('내용 조회: show F03 / 변경 이력: history F03 (같은 --root 옵션을 유지하세요).')
        elif args.command=='worksheet':print(store.worksheet())
        elif args.command=='sync':print('새 버전:',store.sync(args.actor,args.reason))
        elif args.command=='show':
            row=next((r for r in store.current() if r['id']==args.id),None)
            if not row:raise ValueError('알 수 없는 ID')
            if args.output:atomic(args.output,json.dumps(json.loads(row['payload']),ensure_ascii=False,indent=2)+'\n');print(args.output)
            else:row['payload']=json.loads(row['payload']);print(json.dumps(row,ensure_ascii=False,indent=2))
        elif args.command=='history':
            text=json.dumps(store.history(args.id),ensure_ascii=False,indent=2)+'\n'
            if args.output:atomic(args.output,text)
            else:print(text)
        elif args.command in ('revise','reopen'):
            revision=store.revise(args.id,args.revision,args.actor,args.reason,
              json.loads(args.file.read_text()) if args.command=='revise' else None,getattr(args,'kind',None),args.command=='reopen')
            print(f'{args.id} r{revision}: pending. 새 버전을 검토하세요.')
        elif args.command=='decide':print('저장된 판정:',store.decide(args.id,args.revision,args.status,args.reviewer,args.reason))
        else:print('저장된 판정:',store.import_csv(args.file))
    except (ValueError,OSError,sqlite3.Error) as exc:p.exit(1,str(exc)+'\n')
if __name__=='__main__':main()
