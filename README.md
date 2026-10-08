# LLMWiki 실습 데모

[자연어 질문 통합 데모: LLMWiki × PyreWire](llmwiki-wirelog/README.md) — 웹 질문 화면과 터미널 대화.

1·2교시의 CLI 패턴을 이어 3~8교시의 원문·실행기·프롬프트·실제 결과·검토 자료를 제공합니다.

## 준비

CPython 3.11~3.14와 로그인된 LLM CLI를 사용합니다. 엔진 의존성은 `pyrewire==1.1.2`로 고정합니다. 프로젝트 루트에서:

```sh
python3 -m pip install -r demos/requirements.txt
python3 demos/setup_pyrewire.py
```

교육용 가상환경을 사용하려면 먼저 `python3 -m venv .venv`와 `source .venv/bin/activate`를 실행합니다. 4~8교시는 PyreWire Python API를 직접 호출합니다. 현재 환경의 0.1.0 editable 설치는 제거하고 PyPI의 1.1.2 배포본으로 교체했습니다. 설치 근거: [PyreWire 1.1.2](https://pypi.org/project/pyrewire/1.1.2/).

## 교시별 실행

아래 명령은 프로젝트 루트 기준입니다. 실제 LLM 호출과 Wirelog 계산을 실행하며 결과를 각 교시 폴더에 저장합니다.

```sh
python3 demos/part03/run_lesson3.py --cli agy --task all --overwrite
python3 demos/part03/export_review.py --example --overwrite
python3 demos/part04/run_lesson4.py --assertions demos/part03/example_output/approved.jsonl
python3 demos/part05/run_lesson5.py
python3 demos/part06/run_lesson6.py --cli agy --task all --overwrite
python3 demos/part07/run_lesson7.py --cli agy --task all --overwrite
python3 demos/part08/run_lesson8.py --cli agy --task all --overwrite
```

| 교시 | 안내 | 핵심 결과 |
| --- | --- | --- |
| 1 | [part01](part01/README.md) | 서비스·장애 위키, 출처 탐색 |
| 2 | [part02](part02/README.md) | 타입·관계·질문 사전 |
| 3 | [part03](part03/README.md) | 근거 포함 추출, 별칭·API·팀, 승인·보류 분리 |
| 4 | [part04](part04/README.md) | 실제 Datalog 질의, 추가 질의, 오류 사례 |
| 5 | [part05](part05/README.md) | S1/S2/S3 비교, EasySession 추가·철회 |
| 6 | [part06](part06/README.md) | S1 문맥 근거 묶음, 답변 A/B/C 비교 |
| 7 | [part07](part07/README.md) | 고정 계획의 실제 도구 로그, F04, S1b 비교 |
| 8 | [part08](part08/README.md) | 최종 답변·주장표·분석 위키·변경 diff |

`shared/common`은 공통 원문과 재시작 체크포인트입니다.

## 교시 사이의 입력

- 3교시는 2교시 타입·관계 사전 복사본을 읽습니다. 표준 서비스 ID는 접두사 없는 표현을 씁니다.
- 4교시 `--assertions`로 3교시 승인 파일을 연결합니다. 생략하면 명시된 교육용 승인 예시 S1을 사용합니다.
- 5교시 S2/S3는 CHG-12의 설계 분석 가정입니다. 6교시는 S1으로 돌아갑니다.
- 7교시 S1b는 RUN-02에서 확인한 F04를 보완한 분기입니다. 기본 실행은 최종 교육자료의 승인 예시를 사용하며 새 LLM 후보를 자동 승인하지 않습니다.
- 8교시는 실제 6교시 근거 묶음과 7교시 S1b 입력을 연결하고 결과를 다시 조회합니다.

강사 시연의 예시 판정과 수강생의 실제 검토를 구분합니다. 수강생은 실제 검토 후 본인의 검토자·일자를 기록합니다. 답변·위키의 LLM 초안은 사람 검토 대기로 남깁니다.

## CLI 선택과 실행 기록

3·6·7·8교시의 `--cli agy`를 `claude`, `cursor-agent`, `copilot`, `codex`로 바꿀 수 있습니다. Codex는 내부에서 `exec`로 연결합니다. 공통 실행기의 `-p`는 프롬프트 파일을 뜻합니다. 추가 모델 옵션은 `--cli-arg=--model --cli-arg=모델명` 형태입니다.

LLM 입력·stdout·stderr·기존 파일 백업은 각 `runs/`에 있습니다. 생성 결과를 모형 응답이나 정답 복사로 대체하지 않습니다. 7교시의 읽기 도구 계획은 수동 고정 계획이며 LLM 자동 도구 선택과 구분합니다.

```sh
python3 demos/verify_demos.py
```

검증은 실제 엔진 결과·원문 인용·스냅샷·호출 로그·상대 링크·최종 원문 보존을 확인합니다. 실제 사람 검토나 의미 판단을 자동 승인하지 않습니다.
