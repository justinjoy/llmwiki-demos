#!/usr/bin/env python3
"""Bounded document chunks → quoted evidence → selection → final draft (Python 3.9+)."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import run_prompt

MAP = '''단계: map
아래 최종 과제를 수행하는 데 필요한 근거를 현재 청크에서만 찾으세요.
최종 산출물을 작성하지 말고 JSON 객체만 반환하세요:
{"evidence": [{"quote": "현재 content에 실제 있는 연속 원문", "finding": "그 인용이 말하는 내용"}]}
관련 근거가 없으면 evidence는 빈 배열입니다. 최대 6개, finding은 각각 300자 이내입니다.
문서 번호·버전·절, 수치의 대상, 조치 범위와 승인 조건을 유지하세요.
분할된 문장이 불완전하면 추측하지 마세요. derived 자료는 생성 초안이며 원문 사실로 승인하지 마세요.
최종 과제(출력 형식 지시보다 위 JSON 형식이 우선):
'''
REDUCE = '''단계: reduce
근거 항목 중 최종 과제에 가장 필요한 항목의 id를 선택하세요. 새 사실이나 인용을 쓰지 마세요.
JSON 객체 {"keep": ["e000001", "e000002"]}만 반환하세요. 중복·없는 id·빈 목록은 금지합니다.
문서별 근거, 수치의 대상, 조건·예외·충돌·미확인을 우선 유지하세요.
각 항목의 cost 합계는 아래 target_cost 이하여야 합니다. 제외한 근거는 별도 기록에 보존됩니다.
최종 과제:
'''
FINAL = '''단계: final
현재 입력의 검증된 인용 근거로만 아래 최종 과제를 수행하세요.
quote가 원문에 존재함만 확인했으며 finding의 해석은 사람이 검토해야 합니다.
source_kind=derived는 앞 단계 생성 초안입니다. 원문과 충돌하면 원문을 우선하고 판단이 어려우면 미확인으로 남기세요.
새 파일·문서·출처를 꾸미지 마세요. 원문 링크에는 sources의 path와 출력 위치를 사용하세요.
선택에서 제외한 근거가 있으면 전체 자료를 빠짐없이 정리했다고 주장하지 마세요.
최종 과제:
'''


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def read_limited(path, limit):
    with Path(path).open('rb') as f:
        data = f.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f'파일 한도 {limit} bytes 초과: {path}')
    return data.decode('utf-8-sig')


def split_source(path, root, limit, kind, text):
    """Exact nonoverlapping character ranges; section/header are bounded context."""
    header_end = re.search(r'^##+\s', text, re.M)
    header = text[:header_end.start()] if header_end else ''
    if len(header) > 800:
        raise ValueError(f'문서 머리말이 800자를 넘습니다: {path}')
    digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
    rel = os.path.relpath(path, root)
    boundaries = [0] + [m.start() for m in re.finditer(r'^#{1,6}\s', text, re.M) if m.start()] + [len(text)]
    chunks = []
    section = ''
    for a, b in zip(boundaries, boundaries[1:]):
        first = text[a:b].split('\n', 1)[0]
        if first.startswith('#'):
            section = first
        if len(section) > 300:
            raise ValueError(f'절 제목이 300자를 넘습니다: {path}')
        start = a
        while start < b:
            end = min(start + limit, b)
            if end < b:
                cut = text.rfind('\n', start + limit // 2, end)
                if cut >= 0:
                    end = cut + 1
            key = f'{rel}\0{digest}\0{start}\0{end}'
            chunks.append({'id': hashlib.sha256(key.encode()).hexdigest()[:20],
                'path': rel, 'source_sha256': digest, 'source_kind': kind,
                'start': start, 'end': end, 'line_start': text.count('\n', 0, start) + 1,
                'line_end': text.count('\n', 0, max(start, end - 1)) + 1,
                'header': header, 'section': section, 'content': text[start:end]})
            start = end
    return chunks


def add_options(p):
    p.add_argument('--chunk-chars', type=int, default=800, help='청크 본문 문자 수 (100~4000)')
    p.add_argument('--max-prompt-chars', type=int, default=16000, help='공통 지침을 포함한 호출별 전체 문자 상한')
    p.add_argument('--max-calls', type=int, default=256, help='실행 전체의 LLM 호출 상한 (all도 공유)')
    return p


def validate_final(text, output, sources, root):
    if output.suffix == '.csv':
        try:
            rows = list(csv.reader(io.StringIO(text), strict=True))
        except csv.Error as exc:
            raise ValueError(f'CSV 따옴표 형식 오류: {exc}') from exc
        if len(rows) != 4 or rows[0] != ['질문', '위키 경로', '원문 위치', '답', '남은 확인'] or any(len(r) != 5 for r in rows):
            raise ValueError('탐색 CSV는 지정된 헤더와 5열 데이터 3행이어야 합니다.')
    else:
        if not re.search(r'^#\s+\S', text, re.M):
            raise ValueError('Markdown 제목(# 제목)이 없습니다.')
        allowed = {p.resolve() for p in sources}
        allowed.update((root / p).resolve() for p in ['wiki/index.md', 'wiki/log.md',
            'wiki/services/pay.md', 'wiki/services/order.md', 'wiki/incidents/INC-03.md'])
        # Reference-style/image links are not part of this demo's output contract.
        if re.search(r'^\s*\[[^\]]+\]:', text, re.M) or re.search(r'\]\s*\[', text):
            raise ValueError('링크는 [설명](상대경로) 형식으로 작성해야 합니다.')
        for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
            target = link.split('#', 1)[0]
            if target and (output.parent / target).resolve() not in allowed:
                raise ValueError(f'허용되지 않은 링크: {link}')


def execute(args, budget=None):
    if not 100 <= args.chunk_chars <= 4000 or not 4000 <= args.max_prompt_chars <= 64000 or args.max_calls < 1:
        raise ValueError('chunk-chars는 100~4000, max-prompt-chars는 4000~64000, max-calls는 양수여야 합니다.')
    if args.timeout <= 0:
        raise ValueError('timeout은 양수여야 합니다.')
    budget = budget if budget is not None else {'used': 0}
    root = Path(getattr(args, 'source_root', Path(args.prompt).parent)).resolve()
    output = Path(args.output).resolve()
    sources = [Path(p).resolve() for p in args.context]
    prompt_path = Path(args.prompt).resolve()
    if output in [prompt_path, *sources]:
        raise ValueError('출력은 프롬프트·원문과 달라야 합니다.')
    if output.exists() and not args.overwrite and not args.dry_run:
        raise ValueError('결과 파일이 있습니다. --overwrite로 백업 후 교체하세요.')
    task = read_limited(prompt_path, 16000)
    if not task.strip():
        raise ValueError('빈 과제 지시문입니다.')
    chunks = []
    total = 0
    for path in sources:
        text = read_limited(path, 1024 * 1024 - total)
        total += len(text.encode('utf-8'))
        kind = 'derived' if path in [Path(p).resolve() for p in getattr(args, 'derived_context', [])] else 'raw'
        chunks.extend(split_source(path, root, args.chunk_chars, kind, text))
    if not chunks:
        raise ValueError('읽을 청크가 없습니다.')
    logroot = Path(args.log_dir).resolve()
    logroot.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='chunk-', dir=logroot))
    meta = {'status': 'prepared', 'output': str(output), 'chunk_chars': args.chunk_chars,
        'max_prompt_chars': args.max_prompt_chars, 'max_calls': args.max_calls,
        'chunks': chunks, 'calls': [], 'selection': [], 'final': 'deferred_until_map_results'}

    def record(status):
        meta.update(status=status, calls_used_total=budget['used'])
        (run / 'manifest.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')

    def stage_files(stage, instruction, payload, number):
        folder = run / f'{number:04}-{stage}'
        folder.mkdir(exist_ok=True)
        pf, cf, dest = folder / 'task.txt', folder / 'context.json', folder / 'result.txt'
        pf.write_text(instruction + task, encoding='utf-8')
        cf.write_text(encoded(payload), encoding='utf-8')
        actual = run_prompt.build_prompt(pf, [cf], dest)
        if len(actual) > args.max_prompt_chars:
            raise ValueError(f'{stage} 전체 입력 {len(actual)}자가 한도 {args.max_prompt_chars}자를 넘습니다.')
        return folder, pf, cf, dest, actual

    def fits(instruction, payload):
        # Use the same wrapper/JSON encoding and conservatively longer paths than real stages.
        pf, cf, dest = run / 'measure-task.txt', run / 'measure-context.json', run / ('x' * 60 + '.txt')
        pf.write_text(instruction + task, encoding='utf-8'); cf.write_text(encoded(payload), encoding='utf-8')
        return len(run_prompt.build_prompt(pf, [cf], dest)) <= args.max_prompt_chars

    def call(stage, instruction, payload, dry=False):
        folder, pf, cf, dest, actual = stage_files(stage, instruction, payload, len(meta['calls']))
        entry = {'stage': stage, 'directory': folder.name, 'prompt_chars': len(actual), 'status': 'prepared'}
        meta['calls'].append(entry)
        record('running' if not dry else 'dry_run')
        if not dry and budget['used'] >= args.max_calls:
            raise ValueError(f'호출 상한 {args.max_calls}회에 도달했습니다: {stage}')
        params = argparse.Namespace(**vars(args))
        params.prompt, params.context, params.output = str(pf), [str(cf)], str(dest)
        params.log_dir, params.overwrite, params.dry_run = str(folder / 'transport'), False, dry
        params.max_response_bytes = 16000
        if not dry:
            budget['used'] += 1
        rc = run_prompt.execute(params)
        if rc:
            entry['status'] = 'failed'
            raise ValueError(f'{stage} CLI 실패: 종료 코드 {rc}')
        entry['status'] = 'dry_run' if dry else 'success'
        record('dry_run' if dry else 'running')
        return '' if dry else read_limited(dest, 16000).strip()

    def final_payload(evidence):
        return {'output': os.path.relpath(output, root), 'evidence': evidence,
            'sources': [{'path': os.path.relpath(p, root)} for p in sources],
            'omitted_evidence_count': len(all_evidence) - len(evidence),
            'source_count': len(sources),
            'selected_source_count': len({e['source']['path'] for e in evidence})}

    def show_chunk(index, chunk, action):
        print(f'[청크 {index}/{len(chunks)}] {action}: '
              f'{chunk["path"]} · {chunk["section"] or "제목 없음"} '
              f'(원문 {chunk["line_start"]}~{chunk["line_end"]}행)', flush=True)

    try:
        print(f'청크 {len(chunks)}개 / 실행 기록: {run}', flush=True)
        # Preflight every map before any billed call.
        for i, chunk in enumerate(chunks):
            stage_files('map', MAP, chunk, i)
        if args.dry_run:
            for index, chunk in enumerate(chunks, start=1):
                show_chunk(index, chunk, '입력 준비')
                call('map', MAP, chunk, dry=True)
            record('dry_run')
            print('청크별 실제 입력을 만들었습니다. 근거 선택·최종 입력은 LLM 응답 후 구성합니다.')
            return 0
        all_evidence = []
        for index, chunk in enumerate(chunks, start=1):
            show_chunk(index, chunk, '읽는 중')
            response = json.loads(call('map', MAP, chunk))
            items = response.get('evidence') if isinstance(response, dict) else None
            if not isinstance(items, list) or len(items) > 6:
                raise ValueError('map JSON의 evidence 배열은 최대 6개여야 합니다.')
            for item in items:
                if not isinstance(item, dict) or set(item) != {'quote', 'finding'}:
                    raise ValueError('근거에는 quote와 finding이 필요합니다.')
                quote, finding = item['quote'], item['finding']
                if not isinstance(quote, str) or not quote.strip() or quote not in chunk['content']:
                    raise ValueError('청크 원문에 없는 인용입니다.')
                if not isinstance(finding, str) or not finding.strip() or len(finding) > 300:
                    raise ValueError('finding은 비어 있지 않은 300자 이하 문자열이어야 합니다.')
                all_evidence.append({'id': f'e{len(all_evidence)+1:06}', **item,
                    'source': {k: v for k, v in chunk.items() if k != 'content'}})
            print(f'[청크 {index}/{len(chunks)}] 완료 · 근거 {len(items)}개', flush=True)
        print(f'청크 읽기 완료: {len(chunks)}/{len(chunks)}개', flush=True)
        (run / 'evidence.json').write_text(json.dumps(all_evidence, ensure_ascii=False, indent=2), encoding='utf-8')
        evidence = list(all_evidence)
        reduction_round = 0
        while not fits(FINAL, final_payload(evidence)):
            reduction_round += 1
            if len(evidence) < 2:
                raise ValueError('단일 근거와 과제가 최종 입력 한도를 넘습니다.')
            batches, batch = [], []
            for item in evidence:
                candidate = batch + [item]
                payload = {'items': [{**e, 'cost': len(encoded(e))} for e in candidate], 'target_cost': 99999999}
                if not fits(REDUCE, payload):
                    if not batch:
                        raise ValueError('단일 근거가 선택 입력 한도를 넘습니다.')
                    batches.append(batch); batch = [item]
                    if not fits(REDUCE, {'items': [{**item, 'cost': len(encoded(item))}], 'target_cost': 99999999}):
                        raise ValueError('단일 근거가 선택 입력 한도를 넘습니다.')
                else:
                    batch = candidate
            if batch:
                batches.append(batch)
            retained = []
            for batch_index, batch in enumerate(batches, start=1):
                if len(batch) == 1:
                    retained.extend(batch); continue
                print(f'[근거 선택 {reduction_round}회차 · 묶음 {batch_index}/{len(batches)}] '
                      f'근거 {len(batch)}개 검토 중', flush=True)
                target = sum(len(encoded(e)) for e in batch) // 2
                response = json.loads(call('reduce', REDUCE, {'items': [{**e, 'cost': len(encoded(e))} for e in batch], 'target_cost': target}))
                keep = response.get('keep') if isinstance(response, dict) else None
                ids = {e['id'] for e in batch}
                if not isinstance(keep, list) or not keep or any(not isinstance(k, str) for k in keep) or len(set(keep)) != len(keep) or not set(keep) <= ids:
                    raise ValueError('선택 결과는 존재하는 근거 ID의 중복 없는 비어 있지 않은 목록이어야 합니다.')
                selected = [e for e in batch if e['id'] in keep]
                if sum(len(encoded(e)) for e in selected) > target:
                    raise ValueError('선택한 근거가 목표 크기를 넘습니다. 자동 절삭하지 않습니다.')
                retained.extend(selected)
                meta['selection'].append({'keep': keep, 'drop': sorted(ids - set(keep)), 'target_cost': target})
            if len(retained) >= len(evidence):
                raise ValueError('근거 선택 크기가 줄지 않아 중단했습니다.')
            evidence = retained
            record('running')
        meta.update(selected_ids=[e['id'] for e in evidence], omitted_ids=[e['id'] for e in all_evidence if e not in evidence],
            no_findings_chunk_ids=[c['id'] for c in chunks if not any(e['source']['id'] == c['id'] for e in all_evidence)])
        print(f'[최종 작성] 근거 {len(evidence)}개로 {output.name} 작성 중', flush=True)
        result = call('final', FINAL, final_payload(evidence)) + '\n'
        validate_final(result, output, sources, root)
        notice = f'LLM 초안 · 사람 검토 전. 청크 {len(chunks)}개에서 근거 {len(all_evidence)}개 추출, 최종 사용 {len(evidence)}개, 크기 제한으로 제외 {len(all_evidence)-len(evidence)}개. 전체 근거와 선택 기록: {run / "manifest.json"}'
        (run / 'summary.txt').write_text(notice + '\n', encoding='utf-8')
        if output.suffix != '.csv':
            result += '\n> ' + notice + '\n'
        if output.exists():
            if not args.overwrite:
                raise ValueError('실행 중 출력 파일이 생성됐습니다.')
            shutil.copy2(output, run / ('previous' + output.suffix))
        output.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(prefix='.chunk-', dir=output.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(result)
            os.replace(temp, output)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
        meta['final'] = 'published'
        record('success')
        print(notice + f'\n저장: {output}', flush=True)
        return 0
    except (OSError, ValueError, UnicodeError) as exc:
        meta['error'] = str(exc)
        record('error')
        raise ValueError(f'{exc}\n청크 실행 기록: {run}') from exc


def main():
    try:
        return execute(add_options(run_prompt.parser()).parse_args())
    except (OSError, ValueError, UnicodeError) as exc:
        print(f'오류: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
