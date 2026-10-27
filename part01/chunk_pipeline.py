#!/usr/bin/env python3
"""One to three source bundles → verified evidence → final draft (Python 3.9+)."""
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
아래 최종 과제를 수행하는 데 필요한 근거를 현재 청크의 sources에서 찾으세요.
각 근거에 출처 조각의 id를 source_id로 쓰고 그 조각의 content에서만 그대로 인용하세요.
path·section 등의 메타데이터는 인용 대상이 아닙니다. 다른 조각의 문장을 섞거나 보충하지 마세요.
최종 산출물을 작성하지 말고 JSON 객체만 반환하세요:
{"evidence": [{"source_id": "sources의 id", "quote": "그 content에 있는 연속 원문", "finding": "그 인용이 말하는 내용"}]}
관련 근거가 없으면 evidence는 빈 배열입니다. 최대 6개, finding은 각각 300자 이내입니다.
문서 번호·버전·절, 수치의 대상, 조치 범위와 승인 조건을 유지하세요.
분할된 문장이 불완전하면 추측하지 마세요. derived 자료는 생성 초안이며 원문 사실로 승인하지 마세요.
최종 과제(출력 형식 지시보다 위 JSON 형식이 우선):
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


def json_response(text):
    """Accept one JSON value, including a single final object after CLI prose.

    Never choose between multiple objects or extract an inner object from a
    malformed response. Schema and source validation still happen afterward.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError as original:
        objects = []
        end = 0
        for match in re.finditer(r'^\s*(?=\{)', text, re.M):
            start = match.end()
            if start < end:
                continue
            if not objects and any(c in text[:start] for c in '{}[]'):
                raise ValueError('JSON 앞에 객체·배열 구분자가 있어 응답 경계가 모호합니다.') from original
            value, size = json.JSONDecoder().raw_decode(text[start:])
            end = start + size
            objects.append(value)
        if len(objects) != 1 or text[end:].strip() not in {'', '```'}:
            raise ValueError('설명 뒤 JSON 객체 하나만 허용합니다. 여러 객체나 JSON 뒤 설명은 허용하지 않습니다.') from original
        return objects[0]


def validate_map(text, chunk):
    response = json_response(text)
    items = response.get('evidence') if isinstance(response, dict) else None
    if not isinstance(items, list) or len(items) > 6:
        raise ValueError('map JSON의 evidence 배열은 최대 6개여야 합니다.')
    sources = {s['id']: s for s in chunk['sources']}
    validated = []
    for item in items:
        if not isinstance(item, dict) or set(item) != {'source_id', 'quote', 'finding'}:
            raise ValueError('근거에는 source_id, quote, finding이 필요합니다.')
        ident = item['source_id']
        if not isinstance(ident, str) or ident not in sources:
            raise ValueError('source_id는 현재 청크의 sources에 있는 id여야 합니다.')
        source = sources[ident]
        quote, finding = item['quote'], item['finding']
        if not isinstance(quote, str) or not quote.strip() or quote not in source['content']:
            raise ValueError('지정한 출처 범위에 없는 인용입니다. 해당 source_id의 content에서 그대로 복사하세요.')
        if not isinstance(finding, str) or not finding.strip() or len(finding) > 300:
            raise ValueError('finding은 비어 있지 않은 300자 이하 문자열이어야 합니다.')
        validated.append({'quote': quote, 'finding': finding,
                          'source': {k: v for k, v in source.items() if k != 'content'}})
    return validated


def read_limited(path, limit):
    with Path(path).open('rb') as f:
        data = f.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f'파일 한도 {limit} bytes 초과: {path}')
    return data.decode('utf-8-sig')


def source_document(path, root, kind, text):
    header_end = re.search(r'^##+\s', text, re.M)
    header = text[:header_end.start()] if header_end else ''
    if len(header) > 800:
        raise ValueError(f'문서 머리말이 800자를 넘습니다: {path}')
    headings = [(m.start(), m.group()) for m in re.finditer(r'^#{1,6}\s[^\n]*', text, re.M)]
    if any(len(title) > 300 for _, title in headings):
        raise ValueError(f'절 제목이 300자를 넘습니다: {path}')
    return {'path': os.path.relpath(path, root), 'source_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
            'source_kind': kind, 'text': text, 'headings': headings}


def source_fragment(document, start, end):
    text = document['text']
    active = [title for offset, title in document['headings'] if offset <= start]
    inside = [title for offset, title in document['headings'] if start < offset < end]
    titles = active[-1:] + inside
    section = titles[0] if len(titles) == 1 else (titles[0][:130] + ' … ' + titles[-1][:130] if titles else '')
    key = f'{document["path"]}\0{document["source_sha256"]}\0{start}\0{end}'
    return {**{k: document[k] for k in ('path', 'source_sha256', 'source_kind')},
            'id': hashlib.sha256(key.encode()).hexdigest()[:20], 'start': start, 'end': end,
            'line_start': text.count('\n', 0, start) + 1,
            'line_end': text.count('\n', 0, max(start, end - 1)) + 1,
            'section': section, 'content': text[start:end]}


def bundle_sources(documents, count):
    """Balanced task-wide ranges, preserving each file's exact identity/content."""
    total = sum(len(d['text']) for d in documents)
    count = min(count, total)
    boundaries = [0]
    joined = ''.join(d['text'] for d in documents)
    for i in range(1, count):
        ideal = total * i // count
        cut = joined.rfind('\n', max(boundaries[-1] + 1, ideal - min(256, total // (count * 4))), ideal)
        boundaries.append(cut + 1 if cut >= 0 else ideal)
    if total:
        boundaries.append(total)
    chunks = []
    for index, (left, right) in enumerate(zip(boundaries, boundaries[1:]), start=1):
        fragments = []
        offset = 0
        for document in documents:
            length = len(document['text'])
            start, end = max(0, left - offset), min(length, right - offset)
            if start < end:
                fragments.append(source_fragment(document, start, end))
            offset += length
        chunks.append({'id': f'chunk{index:03}', 'sources': fragments})
    return chunks


def add_options(p):
    p.add_argument('--chunk-chars', type=int, default=4800, help='초기 청크 본문 목표 (100자 이상, 호출 수에 맞춰 자동 확대)')
    p.add_argument('--max-prompt-chars', type=int, default=16000, help='전체 입력의 초기 목표 (필요한 실측 크기로 자동 확대)')
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
    if args.chunk_chars < 100 or not 4000 <= args.max_prompt_chars <= 64000 or args.max_calls < 1:
        raise ValueError('chunk-chars는 100 이상, max-prompt-chars 초기 목표는 4000~64000, max-calls는 양수여야 합니다.')
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
    documents = []
    total = 0
    for path in sources:
        text = read_limited(path, 1024 * 1024 - total)
        total += len(text.encode('utf-8'))
        kind = 'derived' if path in [Path(p).resolve() for p in getattr(args, 'derived_context', [])] else 'raw'
        documents.append(source_document(path, root, kind, text))
    if not any(d['text'] for d in documents):
        raise ValueError('읽을 청크가 없습니다.')
    logroot = Path(args.log_dir).resolve()
    logroot.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='chunk-', dir=logroot))
    meta = {'status': 'prepared', 'output': str(output), 'chunk_chars': args.chunk_chars,
        'max_prompt_chars': args.max_prompt_chars, 'max_calls': args.max_calls,
        'requested_chunk_chars': args.chunk_chars, 'requested_prompt_chars': args.max_prompt_chars,
        'effective_prompt_chars': args.max_prompt_chars,
        'chunks': [], 'calls': [], 'selection': [], 'final': 'deferred_until_map_results'}

    def record(status):
        meta.update(status=status, calls_used_total=budget['used'])
        (run / 'manifest.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')

    def grow_capacity(required):
        if required > meta['effective_prompt_chars']:
            print(f'[입력 크기 조정] {meta["effective_prompt_chars"]} → {required}자 (추가 분할·선택 호출 없음)', flush=True)
            meta['effective_prompt_chars'] = required
            meta['max_prompt_chars'] = required

    def stage_files(stage, instruction, payload, number):
        folder = run / f'{number:04}-{stage}'
        folder.mkdir(exist_ok=True)
        pf, cf, dest = folder / 'task.txt', folder / 'context.json', folder / 'result.txt'
        pf.write_text(instruction + task, encoding='utf-8')
        cf.write_text(encoded(payload), encoding='utf-8')
        actual = run_prompt.build_prompt(pf, [cf], dest)
        grow_capacity(len(actual))
        return folder, pf, cf, dest, actual

    def measure(instruction, payload):
        # Reserve room for a bounded correction and conservatively longer paths.
        payload = {**payload, 'validation_feedback': 'x' * 500}
        pf, cf, dest = run / 'measure-task.txt', run / 'measure-context.json', run / ('x' * 60 + '.txt')
        pf.write_text(instruction + task, encoding='utf-8'); cf.write_text(encoded(payload), encoding='utf-8')
        return len(run_prompt.build_prompt(pf, [cf], dest))

    def call(stage, instruction, payload, dry=False, attempt=0):
        folder, pf, cf, dest, actual = stage_files(stage, instruction, payload, len(meta['calls']))
        entry = {'stage': stage, 'directory': folder.name, 'prompt_chars': len(actual),
                 'effective_prompt_chars': meta['effective_prompt_chars'], 'attempt': attempt,
                 'chunk_id': payload.get('id'), 'status': 'prepared'}
        meta['calls'].append(entry)
        record('running' if not dry else 'dry_run')
        if not dry and budget['used'] >= args.max_calls:
            raise ValueError(f'호출 상한 {args.max_calls}회에 도달했습니다: {stage}')
        params = argparse.Namespace(**vars(args))
        params.prompt, params.context, params.output = str(pf), [str(cf)], str(dest)
        params.log_dir, params.overwrite, params.dry_run = str(folder / 'transport'), False, dry
        params.max_response_bytes = 16000
        params.max_prompt_chars = meta['effective_prompt_chars']
        if not dry:
            budget['used'] += 1
        rc = run_prompt.execute(params)
        if rc:
            entry['status'] = 'failed'
            raise ValueError(f'{stage} CLI 실패: 종료 코드 {rc}')
        entry['status'] = 'dry_run' if dry else 'success'
        record('dry_run' if dry else 'running')
        return '' if dry else read_limited(dest, 16000).strip()

    def validated_call(stage, instruction, payload, validator):
        original_payload = payload
        for attempt in range(2):
            response = call(stage, instruction, payload, attempt=attempt)
            entry = meta['calls'][-1]
            try:
                value = validator(response)
            except ValueError as exc:
                entry.update(validation_status='rejected', validation_error=str(exc))
                record('running')
                if attempt == 1:
                    raise
                print(f'[{stage} 재검증] 응답을 거부했습니다. 같은 입력을 한 번 재요청합니다: ' + str(exc), flush=True)
                feedback_error = ''.join(c if c.isprintable() and c not in {'"', '\\'} else ' ' for c in str(exc))[:160]
                payload = {**original_payload, 'validation_feedback':
                    '앞선 응답은 검증에 실패했습니다. 같은 입력으로 오류를 고쳐 지정된 형식의 본문만 반환하세요. '
                    'map은 설명 없이 JSON 객체 하나만, final은 지정된 문서 본문만 반환하세요. ' + feedback_error}
            else:
                entry['validation_status'] = 'accepted'
                record('running')
                return value

    def final_payload(evidence):
        return {'output': os.path.relpath(output, root), 'evidence': evidence,
            'sources': [{'path': os.path.relpath(p, root)} for p in sources],
            'omitted_evidence_count': 0,
            'source_count': len(sources),
            'selected_source_count': len({e['source']['path'] for e in evidence})}

    def show_chunk(index, chunk, action):
        print(f'[청크 {index}/{len(chunks)}] {action}: 출처 조각 {len(chunk["sources"])}개', flush=True)
        for source in chunk['sources']:
            print(f'  {source["path"]} · {source["section"] or "제목 없음"} '
                  f'(원문 {source["line_start"]}~{source["line_end"]}행)', flush=True)

    try:
        total_chars = sum(len(d['text']) for d in documents)
        group_limit = min(3, max(1, (total_chars + args.chunk_chars - 1) // args.chunk_chars))
        for count in range(1, group_limit + 1):
            chunks = bundle_sources(documents, count)
            required = max(measure(MAP, chunk) for chunk in chunks)
            if required <= args.max_prompt_chars:
                break
        grow_capacity(required)
        effective_chars = max(sum(len(s['content']) for s in c['sources']) for c in chunks)
        meta.update(chunks=chunks, effective_chunk_chars=effective_chars, initial_map_groups=len(chunks))
        print(f'청크 {len(chunks)}개 / 본문 목표 {args.chunk_chars}자 → 실제 최대 {effective_chars}자 / 실행 기록: {run}', flush=True)
        # Preflight every map before any billed call.
        for i, chunk in enumerate(chunks):
            stage_files('map', MAP, chunk, i)
        if args.dry_run:
            for index, chunk in enumerate(chunks, start=1):
                show_chunk(index, chunk, '입력 준비')
                call('map', MAP, chunk, dry=True)
            record('dry_run')
            print('최대 3개 청크의 실제 입력을 만들었습니다. 최종 입력은 근거 응답 후 구성합니다.')
            return 0
        all_evidence = []
        for index, chunk in enumerate(chunks, start=1):
            show_chunk(index, chunk, '읽는 중')
            items = validated_call('map', MAP, chunk, lambda text: validate_map(text, chunk))
            for item in items:
                all_evidence.append({'id': f'e{len(all_evidence)+1:06}', **item})
            print(f'[청크 {index}/{len(chunks)}] 완료 · 근거 {len(items)}개', flush=True)
        print(f'청크 읽기 완료: {len(chunks)}/{len(chunks)}개', flush=True)
        (run / 'evidence.json').write_text(json.dumps(all_evidence, ensure_ascii=False, indent=2), encoding='utf-8')
        evidence = list(all_evidence)
        grow_capacity(measure(FINAL, final_payload(evidence)))
        meta.update(selected_ids=[e['id'] for e in evidence], omitted_ids=[],
            no_findings_source_ids=[s['id'] for c in chunks for s in c['sources']
                                   if not any(e['source']['id'] == s['id'] for e in all_evidence)])
        print(f'[최종 작성] 근거 {len(evidence)}개로 {output.name} 작성 중', flush=True)
        def final_response(text):
            validate_final(text, output, sources, root)
            return text + '\n'
        result = validated_call('final', FINAL, final_payload(evidence), final_response)
        notice = f'LLM 초안 · 사람 검토 전. 청크 {len(chunks)}개에서 근거 {len(all_evidence)}개 추출, 모두 최종 작성에 전달. 근거 추출은 전체 사실의 완전한 정리가 아닙니다. 실행 기록: {run / "manifest.json"}'
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
