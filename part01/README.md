# 1교시 · LLMWiki 구축과 지식 탐색

이 폴더만으로 실행할 수 있는 1교시 데모입니다. Python 3.9 이상과 로그인된 LLM CLI가 필요합니다. Wirelog 설치는 필요하지 않습니다.

## 시작

프로젝트 루트의 터미널에서 실행합니다.

```sh
cd demos/part01
python3 run_lesson1.py --cli agy --task pay --dry-run
python3 run_lesson1.py --cli agy --task pay --overwrite
```

첫 명령은 문서를 나누고 청크별 실제 입력을 생성합니다. 두 번째 명령은 청크마다 LLM을 호출해 근거를 추출하고, 그 근거로 `wiki/services/pay.md`를 작성합니다. 기존 내용은 모든 단계가 성공한 뒤 `runs/`에 백업합니다. 최종 작성 입력은 청크별 응답을 받은 뒤 구성하므로 dry-run에는 없습니다.

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

## 문서를 나눠 읽는 방법

1. 원문을 제목·절 경계에서 나눕니다. 긴 절은 본문 800자 이하로 더 나눕니다. 각 청크에 문서 머리말, 절 제목, 파일명과 원문 위치를 붙입니다.
2. 청크 하나씩 LLM에 전달해 과제에 필요한 인용과 설명을 받습니다. 인용문이 그 청크에 실제 존재하는지 검사합니다.
3. 근거가 많으면 묶음을 나눠 필요한 근거의 ID를 선택합니다. 선택에서도 한 번에 전부 넣지 않습니다. 여러 번 선택할 수 있으며, 원래 근거와 제외한 ID를 기록합니다.
4. 선택한 근거만으로 최종 페이지를 작성합니다. 파일 형식과 링크 경로를 검사한 뒤 저장합니다.

`pay`뿐 아니라 `order`, `incident`, `index`, `explore`, `log`에도 같은 방식을 적용합니다. 앞에서 생성한 위키도 나눠 읽으며 원문과 구분해 `derived`(생성 초안)로 표시합니다. 다른 교시 실행기는 이번 변경 대상이 아닙니다.

### 진행 상황 표시

시작할 때 총 청크 수를 표시하고, 각 호출 직전에 현재 번호·파일명·절·원문 행 범위를 출력합니다. 인용 검증까지 성공하면 완료와 근거 수를 표시합니다.

```text
청크 15개 / 실행 기록: …
[청크 3/15] 읽는 중: raw/ARCH-01_v1.md · ## 2. 결제 내역 기록과 타임아웃 (원문 17~30행)
[청크 3/15] 완료 · 근거 4개
…
청크 읽기 완료: 15/15개
[근거 선택 1회차 · 묶음 1/3] 근거 18개 검토 중
[최종 작성] 근거 12개로 pay.md 작성 중
```

위 숫자는 표시 예시입니다. `--dry-run`에서는 실제로 읽었다고 표시하지 않고 `[청크 3/15] 입력 준비`로 구분합니다. `--task all`에서는 각 작업의 청크 번호가 1부터 다시 시작합니다.

### 크기와 호출 수

```sh
python3 run_lesson1.py --cli agy --task pay --chunk-chars 800 --max-prompt-chars 16000 --max-calls 256 --overwrite
```

- 기본 청크 본문은 800자입니다. 전체 LLM 입력은 공통 지침·과제·메타데이터·JSON을 포함해 호출당 16,000자 이하입니다. 문자 수이며 모델별 토큰 수와 다릅니다.
- 입력 파일 합계는 작업당 1 MiB, 호출별 응답은 16,000 bytes로 제한합니다. 머리말 800자·절 제목 300자를 넘는 문서는 먼저 정리해야 합니다. 출력 로그의 실시간 디스크 할당량을 제한하는 기능은 아닙니다.
- 기본 최대 호출은 실행 전체 256회입니다. `--task all`도 같은 예산을 공유합니다. 여러 청크와 선택 단계 때문에 작업 하나에도 여러 번 호출하며 비용·시간이 증가합니다.
- 잘못된 JSON·인용·링크·CSV, 한도 초과, CLI 실패는 해당 작업을 중단합니다. 해당 작업의 기존 결과는 보존하며, `all`에서 이미 성공한 앞 단계 결과는 남습니다. 자동 재시도나 캐시·재시작 기능은 없습니다.

선택 과정은 일부 근거를 제외할 수 있습니다. Markdown 결과 끝과 실행 요약에 사용·제외 건수를 표시합니다. CSV는 5열 3행 형식을 유지하므로 콘솔과 해당 실행 폴더의 `summary.txt`에서 확인합니다. 정확한 인용문이 있다고 설명까지 옳다는 뜻은 아닙니다. 사람의 원문 대조가 필요합니다.

## 다른 파일에도 청킹 적용

`-p`로 프롬프트 파일, `-c`로 원문 파일, `-o`로 결과 파일을 지정합니다.

```sh
python3 chunk_pipeline.py --cli agy -p prompt.txt -c raw/ARCH-01_v1.md -c raw/ADR-07_v1.md -c raw/INC-03_v1.md -o wiki/services/pay.md --overwrite
```

## 파일과 제출물

- `raw/`: 아키텍처·설계 결정·장애 보고서 원문 3개. 교육용 합성 사례입니다.
- `prompt.txt`, `prompts/`: 단계별 프롬프트.
- `wiki/`: 서비스·장애 페이지, 탐색 입구, 변경 기록.
- `exploration.csv`: 세 질문의 답과 탐색 경로·근거.
- `review.md`: 수강생이 직접 작성할 검토·수정 기록.
- `chunk_pipeline.py`: 문서 분할·근거 검증·크기 제한·선택·최종 저장.
- `run_prompt.py`: 개별 CLI 호출을 담당하는 하위 실행기. 직접 호출하면 청킹하지 않습니다.
- `runs/chunk-*/manifest.json`: 청크 원문·위치·해시, 단계와 호출 수, 선택·제외한 근거 ID, 성공·실패 상태.
- `runs/chunk-*/evidence.json`: 선택 전 전체 추출 근거. `summary.txt`: 사용·제외 개수. `previous.md` 또는 `previous.csv`: 기존 결과 백업.
- `runs/chunk-*/*/transport/*/`: 실제 `input.txt`, `stdout.txt`, `stderr.txt`, `run.json`. 실행할 때 생성됩니다.

위키의 출처와 상대 링크를 검토하세요. 25분·42분은 과거 사고의 관측값이며 미래 복구 보장이 아닙니다. 생성한 답변과 변경 기록은 사람 검토 전의 초안입니다.

정답 예제는 이 데모에 포함하지 않았습니다.
