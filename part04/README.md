# 4교시 · Datalog 모델링과 Wirelog 연결

[최종 슬라이드](../../slides/part04.pptx) · [전체 슬라이드 안내](../../slides/README.md)

승인 사실을 Datalog로 투영하고 PyreWire 1.1.2 Python API로 기본 질의와 추가 질의를 실행합니다.

기준 자료는 [최종 인포그래픽 슬라이드](../../output/인포그래픽_개정본/PPT/04_Datalog_모델링과_Wirelog_연결_v4.pptx)와 그 교육자료입니다. [슬라이드별 연결](SLIDE_MAP.md)을 참고하세요. 각 실습 A는 슬라이드 10의 10분, B는 슬라이드 12의 13분입니다.

## 바로 실행

프로젝트 루트에서 `python3 -m pip install -r demos/requirements.txt`와 `python3 demos/setup_pyrewire.py`로 PyreWire 1.1.2를 준비한 뒤 실행합니다.

```sh
cd demos/part04
python3 run_lesson4.py --task all
```

CPython 3.11~3.14와 `pyrewire==1.1.2`를 사용합니다. 엔진은 `EasySession.snapshot()`을 직접 호출합니다. 6~8교시의 `--cli`는 LLM 실행 파일(`agy`, `claude`, `codex`, `cursor-agent`, `copilot`)만 선택합니다.

| 실습 | 산출물 |
| --- | --- |
| A | model.dl, facts.dl, lesson.dl, result.json |
| B | queries.dl, extended_result.json, invalid_result.json, direction_result.json |

## 실습 A · 슬라이드 10 · 10분

1. `model.dl`의 선언·규칙과 `facts.dl`의 세 직접 호출·세 about 사실을 확인합니다(3분).
2. `python3 run_lesson4.py --task query`로 실제 Wirelog를 실행합니다(3분).
3. `result.json`의 direct 3개, pay_doc 2개를 튜플 집합으로 비교합니다(4분).

기본 입력은 최종 교육자료의 S1 승인 예시입니다. 본인의 3교시 승인 결과를 연결하려면:

```sh
python3 run_lesson4.py --assertions ../part03/approved.jsonl --task all
```

`pending`이나 빈 승인 파일은 차단합니다. 강사 시연은 `../part03/example_output/approved.jsonl`을 지정해 연결할 수 있습니다. `input.json`에 입력 출처를 남깁니다. API·팀은 3교시 `entities.json`에 보존하고 실행 모델은 depends_on/about으로 투영합니다.

## 실습 B · 슬라이드 12 · 13분

```sh
python3 run_lesson4.py --task extend
python3 run_lesson4.py --task invalid
```

`queries.dl`의 order_doc과 shop_dep을 읽고 각각 `ADR-07:v1`, `order`가 나오는 이유를 설명합니다. 잘못된 열 수는 `invalid_result.json`에 실제 파서 오류로 기록됩니다. 역방향 입력은 `direction_result.json`에서 실행에 성공하므로 원문 대조가 필요합니다. `errors/`의 입력과 결과를 함께 제출합니다.

## 확인 문제 · 슬라이드 15~16

- 새 `EasySession`을 여는 것은 새 평가입니다. 같은 세션의 증분 갱신은 5교시에서 별도로 확인합니다.
- 두 인자가 모두 symbol이면 타입 검사만으로 호출 방향 오류를 찾을 수 없습니다.

다음 교시에서는 재귀 규칙과 `EasySession.insert/remove/step`을 사용합니다. 문자열 사실은 공개 `intern()` API로 이름을 등록하여 결과에서도 원래 서비스 ID를 유지합니다.

## 실행 기록과 제출

LLM 실행은 실제 입력·stdout·stderr·상태를 runs/에 남깁니다. `--overwrite`는 기존 LLM 결과를 백업한 뒤 교체합니다. 실패·빈 응답·시간 초과는 성공 결과로 대체하지 않습니다. Datalog 실행은 입력과 실제 엔진 출력을 저장하며 이전 결과도 백업합니다.

[최종 교육자료의 해설](reference/ANSWER.md)은 실습 후 비교용입니다. `review.md`에는 본인의 실제 검토를 기록하세요. 모든 원문은 교육용 합성 사례입니다.

3교시의 버전 관리 승인 파일은 `approved.meta.json`과 `.review/state.sqlite3`를 함께 확인합니다. 후보가 수정·재검토 중이면 해당 입력은 거부됩니다. [재검토 절차](../part03/REVIEW_WORKFLOW.md)에 따라 최신 판정을 내보낸 후 다시 실행하세요.
