# 2교시 · 온톨로지 설계

[최종 슬라이드](../../slides/part02.pptx) · [전체 슬라이드 안내](../../slides/README.md)

업무 문서를 타입·관계·질문 사전으로 정리하고, 이름과 문서 버전이 만드는 반례로 검토합니다. PPT 10번의 실습 A와 12번의 실습 B에 대응합니다.

이 폴더만으로 실행할 수 있습니다. Python 3.9 이상과 로그인된 LLM CLI가 필요하며, Wirelog 설치는 필요하지 않습니다. 1교시 위키를 완성했다면 함께 살펴보되 자동 입력은 이 폴더에 있는 원문과 앞 단계 산출물로 한정합니다.

## 첫 실행

프로젝트 루트에서 터미널을 열고 다음과 같이 실행합니다.

```sh
cd demos/part02
python3 run_lesson2.py --cli agy --task types --dry-run
python3 run_lesson2.py --cli agy --task types --overwrite
```

첫 명령은 실제 입력을 `runs/`에 만들고 LLM은 호출하지 않습니다. 두 번째 명령은 원문 3개와 `prompt.txt`를 `agy -p`로 전달하고 응답을 `types.csv`에 저장합니다. 배포된 TODO 템플릿이나 기존 결과는 실행 기록 폴더의 `previous.csv`에 백업합니다.

`--cli`에는 다음 실행 파일을 지정할 수 있습니다.

| 도구 | 지정 값 | 내부 호출 |
| --- | --- | --- |
| Antigravity | `agy` | `agy -p 프롬프트본문` |
| Claude | `claude` | `claude --output-format text -p 프롬프트본문` |
| Cursor | `cursor-agent` | `cursor-agent --output-format text -p 프롬프트본문` |
| GitHub Copilot | `copilot` | `copilot --silent -p 프롬프트본문` |
| Codex | `codex` | `codex exec`의 표준 입력 |

Codex의 `-p`는 프로필 옵션이므로 스크립트가 `exec`로 연결합니다. Cursor 실행 파일이 `agent`이면 해당 이름 또는 절대 경로를 지정합니다. 추가 CLI 옵션은 `--cli-arg=--model --cli-arg=모델명`처럼 인자별로 전달합니다. CLI는 응답 본문을 텍스트로 출력하는 모드를 사용하세요.

## 실습 A: 최소 온톨로지 정의

선택한 업무 질문은 다음과 같습니다.

1. ledger 지연 때 호출 경로상 어떤 서비스를 점검할 것인가?
2. pay의 운영 책임은 어느 팀이며 현재 당직자는 누구인가?
3. 대사 큐 소비를 멈추는 조치를 현재 적용할 수 있는가?

`types` 실행 결과를 원문과 대조한 뒤 아래 단계를 실행합니다.

```sh
python3 run_lesson2.py --cli agy --task relations --overwrite
python3 run_lesson2.py --cli agy --task questions --overwrite
```

| 단계 | 프롬프트 | 입력 | 출력 |
| --- | --- | --- | --- |
| types | `prompt.txt` | ARCH-01 v1, ADR-07 v1, INC-03 v1 | `types.csv` |
| relations | `prompts/relations.txt` | 원문 3개 + 타입 사전 | `relations.csv` |
| questions | `prompts/questions.txt` | 원문 3개 + 타입·관계 사전 | `questions.csv` |

타입 정의, 관계 방향·포함·제외 기준, 각 질문의 조회 방향을 검토합니다. 특히 API의 제공 서비스와 운영 담당 팀을 구분하세요. 간접 호출 경로를 직접 호출 사실에 섞지 않습니다. 정책의 구체적 조건과 현재 당직자는 제공된 원문만으로 모두 답할 수 없습니다.

CSV 응답의 헤더가 템플릿과 같은지, 쉼표를 포함하는 셀이 큰따옴표로 묶였는지 확인합니다. 타입·관계·질문을 수정했다면 저장 후 다음 단계를 실행하세요.

## 실습 B: 반례로 모델 검증

```sh
python3 run_lesson2.py --cli agy --task decisions --overwrite
```

이 단계는 `raw/ARCH-01_v2.md`를 추가로 읽고, 세 CSV의 모델을 검토하여 `decisions.md`를 작성합니다.

- payment와 pay는 이름만 보고 합칠 수 있는가?
- ARCH-01의 버전이 v2로 올라가면 운영 구성도 바뀐 것인가?
- ledger와 ledger-db를 구분하는 타입이 필요한가? 개체 정보는 실제 원문에 있는가?
- 호출 서비스 → API → 제공 서비스 방향에서 직접 의존 관계를 설명할 수 있는가?

GLOSS-01과 OPS-04 전문은 이 폴더에 없습니다. 다음 교시에서 확인할 사항을 이미 읽은 사실처럼 인용하지 마세요. 검토서에 수정 제안이 있으면 수강생이 CSV를 고치고 `review.md`에 이유를 기록합니다. 스크립트가 검토 제안을 CSV에 자동 반영하지는 않습니다.

## 전체 시연

네 단계를 순서대로 실행하려면 다음 명령을 사용합니다. LLM을 네 번 호출하며, 앞 단계의 저장된 결과를 다음 입력에 포함합니다.

```sh
python3 run_lesson2.py --cli agy --task all --overwrite
```

중간 오류나 선행 파일의 TODO가 발견되면 중단합니다. 이미 성공한 파일과 실행 기록은 남으므로 실패한 단계부터 재실행할 수 있습니다. `--dry-run --task all`은 현재 파일로 입력을 미리 만들며 실제 응답을 생성하지 않습니다.

## 공통 실행기 직접 사용

공통 실행기의 `-p`는 프롬프트 파일, `-c`는 참고 파일, `-o`는 결과 파일입니다.

```sh
python3 run_prompt.py --cli agy -p prompt.txt -c raw/ARCH-01_v1.md -c raw/ADR-07_v1.md -c raw/INC-03_v1.md -o types.csv --overwrite
```

실제 프롬프트와 원문 내용은 `runs/날짜-고유번호/input.txt`, 응답은 `stdout.txt`, CLI 오류는 `stderr.txt`, 실행 상태는 `run.json`에 남습니다. 공통 실행기는 실패·빈 응답·시간 초과 시 결과 파일을 교체하지 않습니다. 기본 대기 시간은 호출당 300초이며 `--timeout 600`처럼 바꿀 수 있습니다.

## 제출과 검토

제출물은 `types.csv`, `relations.csv`, `questions.csv`, `decisions.md`, `review.md`와 실행 기록입니다. 생성된 사전과 검토서는 초안이며 실제 검토자와 일자는 본인이 기록합니다.

```sh
python3 check_links.py .
```

이 명령은 Markdown의 상대 파일 링크만 검사합니다. CSV 형식, 관계의 의미, 원문 인용의 정확성은 사람이 확인합니다. 원문은 실무 형식을 재현한 교육용 합성 사례이며 정답 파일은 이 데모에 포함하지 않았습니다.
