# 7교시 · LLM과 Wirelog의 검색 협업

수동 계획에 따라 읽기 도구를 실행하고 새 단서 F04와 S1b의 차이를 확인합니다.

실습 A는 10분, 실습 B는 13분 동안 진행합니다.

## 바로 실행

프로젝트 루트에서 `python3 -m pip install -r demos/requirements.txt`와 `python3 demos/setup_pyrewire.py`로 PyreWire 1.1.2를 준비한 뒤 실행합니다.

```sh
cd demos/part07
python3 run_lesson7.py --cli agy --task all --overwrite
```

CPython 3.11~3.14와 `pyrewire==1.1.2`를 사용합니다. 엔진은 `EasySession.snapshot()`을 직접 호출합니다. 6~8교시의 `--cli`는 LLM 실행 파일(`agy`, `claude`, `codex`, `cursor-agent`, `copilot`)만 선택합니다.

| 실습 | 산출물 |
| --- | --- |
| A | plan.json, tool_contracts.json, S1_log.json |
| B | F04_pending.json, S1b_log.json, S1b_input.json, comparison.json, decision.md |

## 실습 A · 10분

```sh
python3 run_lesson7.py --task inspect
```

`plan.json`은 사람이 정한 수업용 고정 계획입니다. 도우미는 이 흐름으로 실제 Wirelog와 원문 읽기를 연결합니다. LLM이 도구를 자동 선택하는 자율 실행이 아닙니다.

| 순서 | 도구 | 출력과 다음 단계 |
| --- | --- | --- |
| 1 | find_candidates | S1 후보 shop/order/pay |
| 2 | find_documents | 첫 about 문서 3개 |
| 3 | search_context | 초기 문서 전체 절 읽기 |
| 4 | search_context | ADR-07 §3에서 OPS-04 확장 |
| 5 | search_context | ARCH-01 §4에서 RUN-02 확장 |
| 6 | trace_path | Python 근거 계층의 F01/F02/F03 경로 |

질문 분해 2분, 실제 도구 실행·원문 읽기 5분, 입력·출력·선택 이유 기록 3분입니다. `S1_log.json`에 각 호출 인자·상태·결과·확장 이유·종료 이유·실제 엔진 출력을 저장합니다.

## 실습 B · 13분

```sh
python3 run_lesson7.py --cli agy --task extract --overwrite
python3 run_lesson7.py --task compare
python3 run_lesson7.py --cli agy --task decision --overwrite
```

4분 동안 F04의 notify → order 호출과 RUN-02 §2를 검토합니다. 다음 4분은 승인 과정을 연습하고 교육자료의 S1b 승인 체크포인트를 선택합니다. 마지막 5분은 재질의 결과·업무 영향·종료 사유를 설명합니다.

기본 비교는 **최종 교육자료의 승인 예시**로 실행합니다. `F04_pending.json`은 자동 승인하지 않습니다. 본인 실습에서는 후보를 `F04_approved.json`으로 복사한 뒤 실제 검토자가 `review_status`를 approved로, `reviewer`를 본인 식별자로 변경하고 실행합니다.

```sh
python3 run_lesson7.py --task compare --approved-f04 F04_approved.json
```

S1b 후보는 4개이며 notify의 사실 ID 경로는 F04/F02/F03입니다. S1b는 S1의 지식 보완 분기이며 S2/S3 설계 변경과 섞지 않습니다. notify의 영향은 알림 지연 점검이며 결제 실패로 단정하지 않습니다.

## 확인 문제

새 관계는 표준 ID·방향·인용 검토 후 반영합니다. error는 조회 실패, empty는 조회 성공 후 결과 없음입니다. 호출 예산은 실행당 6회이며 동일 도구·동일 인자 반복을 차단합니다. `decision.md`는 LLM의 해석 초안이므로 도구 로그와 대조합니다.

## 실행 기록과 제출

LLM 실행은 실제 입력·stdout·stderr·상태를 runs/에 남깁니다. `--overwrite`는 기존 LLM 결과를 백업한 뒤 교체합니다. 실패·빈 응답·시간 초과는 성공 결과로 대체하지 않습니다. Datalog 실행은 입력과 실제 엔진 출력을 저장하며 이전 결과도 백업합니다.

[최종 교육자료의 해설](reference/ANSWER.md)은 실습 후 비교용입니다. `review.md`에는 본인의 실제 검토를 기록하세요. 모든 원문은 교육용 합성 사례입니다.
