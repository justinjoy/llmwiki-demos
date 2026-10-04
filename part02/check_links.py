"""Check relative Markdown file targets. Does not validate meaning or heading anchors."""
import argparse,re
from pathlib import Path
from urllib.parse import unquote

def check(folder):
    errors=[]
    for file in Path(folder).rglob('*.md'):
        text=re.sub(r'```.*?```', '', file.read_text(encoding='utf-8'), flags=re.S)
        for target in re.findall(r'\]\(([^)]+)\)',text):
            if '://' in target or target.startswith(('mailto:','#')):continue
            path=unquote(target.split('#',1)[0].strip('<>'))
            if path and not (file.parent/path).exists():errors.append(f'{file}: {target}')
    return errors
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder');a=p.parse_args();errors=check(a.folder)
    print('\n'.join(errors) if errors else '상대 파일 링크 정상. 원문 의미와 절 번호는 사람이 확인하세요.')
    raise SystemExit(bool(errors))
