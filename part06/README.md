# 6교시 · 추론 결과를 확장하는 LLM 검색

S1으로 복귀하여 원문에서 설계 이유·조치 조건·관측 시간의 의미를 보완합니다.

실습 A는 10분, 실습 B는 13분 동안 진행합니다.

## 바로 실행

프로젝트 루트에서 `python3 -m pip install -r demos/requirements.txt`와 `python3 demos/setup_pyrewire.py`로 PyreWire 1.1.2를 준비한 뒤 실행합니다.

```sh
cd demos/part06
python3 run_lesson6.py --cli agy --task all --overwrite
```

CPython 3.11~3.14와 `pyrewire==1.1.2`를 사용합니다. 엔진은 `EasySession.snapshot()`을 직접 호출합니다. 6~8교시의 `--cli`는 LLM 실행 파일(`agy`, `claude`, `codex`, `cursor-agent`, `copilot`)만 선택합니다.

| 실습 | 산출물 |
| --- | --- |
| A | S1_result.json, input.json, evidence_bundle.json |
| B | comparison.csv, search_plan.md |

## 실습 A · 10분

```sh
python3 run_lesson6.py --cli agy --task evidence --overwrite
```

S1을 실제 Wirelog로 조회하여 `input.json`을 만들고, 원문 4개를 LLM에 전달합니다. 2분 동안 후보·초기 문서를 확인하고, 4분 동안 생성된 근거를 읽고, 4분 동안 원문과 대조합니다.

- 초기 about: ARCH-01 v1, ADR-07 v1, INC-03 v1.
- 확장: ADR-07 §3이 참조하는 OPS-04 v1.
- `evidence_bundle.json`: 문서 ID·버전·절·정확한 quote, 설명·해석·현재 정보 공백을 분리합니다.
- shop의 about 문서가 없더라도 구조적 후보에서 제외하지 않습니다.

원문에 없는 인용, 누락된 정책·시간 근거, 바뀐 후보 집합은 실행 중 검사합니다. 의미·적용 조건은 사람이 확인합니다.

## 실습 B · 13분

```sh
python3 run_lesson6.py --cli agy --task compare --overwrite
python3 run_lesson6.py --cli agy --task plan --overwrite
```

A ‘전체 결제 재시도 즉시 중지’, B ‘조건·승인 후 영향 대사 큐만 제어’, C ‘다음 사고도 25분 내 복구’를 비교합니다. 4분 동안 판정을 검토하고, 4분 동안 조건과 시간을 수정하고, 5분 동안 현재 필요한 증거를 정리합니다.

## 확인 문제

OPS-04 문서 승인과 현재 사고의 실행 승인은 별개입니다. 25분은 신규 주문 처리 정상화, 42분은 지연 주문 대사 완료입니다. 현재 지표·불일치 목록·영향 범위·승인 기록·향후 복구 시각은 제공되지 않았습니다.

7교시는 이 문맥에 RUN-02를 추가하고, 8교시는 실제 `evidence_bundle.json`을 읽습니다.

## 실행 기록과 제출

LLM 실행은 실제 입력·stdout·stderr·상태를 runs/에 남깁니다. `--overwrite`는 기존 LLM 결과를 백업한 뒤 교체합니다. 실패·빈 응답·시간 초과는 성공 결과로 대체하지 않습니다. Datalog 실행은 입력과 실제 엔진 출력을 저장하며 이전 결과도 백업합니다.

[최종 교육자료의 해설](reference/ANSWER.md)은 실습 후 비교용입니다. `review.md`에는 본인의 실제 검토를 기록하세요. 모든 원문은 교육용 합성 사례입니다.
