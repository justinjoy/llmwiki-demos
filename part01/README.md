# 1교시 · LLMWiki 구축과 지식 탐색

[최종 슬라이드](../../slides/part01.pptx) · [전체 슬라이드 안내](../../slides/README.md)

이 폴더만으로 실행할 수 있는 1교시 데모입니다. Python 3.9 이상과 로그인된 LLM CLI가 필요합니다. Wirelog 설치는 필요하지 않습니다.

## 시작

프로젝트 루트의 터미널에서 실행합니다.

```sh
cd demos/part01
python3 run_lesson1.py --cli agy --task pay --dry-run
python3 run_lesson1.py --cli agy --task pay --overwrite
```

첫 명령은 실제 입력만 생성합니다. 두 번째 명령은 원문 3개와 `prompt.txt`를 `agy -p`로 전달하고 결과를 `wiki/services/pay.md`에 저장합니다. 기존 내용은 `runs/`에 백업합니다.

`--cli`는 `agy`(Antigravity), `claude`, `cursor-agent`, `copilot`, `codex`로 바꿀 수 있습니다. Codex는 내부에서 `exec`로 연결합니다. [상세 실행 안내](CLI_GUIDE.md)를 참고하세요.

## 실습 순서

실습 A는 서비스 위키 생성과 검토, 실습 B는 장애 위키와 링크 탐색입니다. 각 실행 후 생성 내용을 원문과 대조하고 다음 단계로 진행하세요.

```sh
# 실습 A: pay를 검토한 뒤 order 생성
python3 run_lesson1.py --cli agy --task order --overwrite

# 실습 B
python3 run_lesson1.py --cli agy --task incident --overwrite
python3 run_lesson1.py --cli agy --task index --overwrite
python3 run_lesson1.py --cli agy --task explore --overwrite
python3 run_lesson1.py --cli agy --task log --overwrite
python3 check_links.py wiki
```

강사 시연에서 6단계를 연속 실행하려면 아래 명령을 사용합니다. 중간 실패 시 이후 단계는 실행하지 않습니다.

```sh
python3 run_lesson1.py --cli agy --task all --overwrite
```

## 공통 프롬프트 실행기

`-p`로 프롬프트 파일, `-c`로 원문 파일, `-o`로 결과 파일을 지정합니다.

```sh
python3 run_prompt.py --cli agy -p prompt.txt -c raw/ARCH-01_v1.md -c raw/ADR-07_v1.md -c raw/INC-03_v1.md -o wiki/services/pay.md --overwrite
```

## 파일과 제출물

- `raw/`: 아키텍처·설계 결정·장애 보고서 원문 3개. 교육용 합성 사례입니다.
- `prompt.txt`, `prompts/`: 단계별 프롬프트.
- `wiki/`: 서비스·장애 페이지, 탐색 입구, 변경 기록.
- `exploration.csv`: 세 질문의 답과 탐색 경로·근거.
- `review.md`: 수강생이 직접 작성할 검토·수정 기록.
- `runs/`: 실제 입력, CLI 응답·오류, 상태 기록, 기존 파일 백업. 실행할 때 생성됩니다.

위키의 출처와 상대 링크를 검토하세요. 25분·42분은 과거 사고의 관측값이며 미래 복구 보장이 아닙니다. 생성한 답변과 변경 기록은 사람 검토 전의 초안입니다.

PPT 10번·12번 슬라이드의 실습에 대응합니다. 정답 예제는 이 데모에 포함하지 않았습니다.
