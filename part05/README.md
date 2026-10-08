# 5교시 · 관계와 규칙을 이용한 추론 검색

재귀 규칙으로 경로와 점검 후보를 찾고 설계 비교와 세션 철회를 구분합니다.

실습 A는 10분, 실습 B는 13분 동안 진행합니다.

## 바로 실행

프로젝트 루트에서 `python3 -m pip install -r demos/requirements.txt`와 `python3 demos/setup_pyrewire.py`로 PyreWire 1.1.2 이상을 준비한 뒤 실행합니다.

```sh
cd demos/part05
python3 run_lesson5.py --task all
```

CPython 3.11~3.14와 `pyrewire>=1.1.2`를 사용합니다. 엔진은 `EasySession.snapshot()`을 직접 호출합니다. 6~8교시의 `--cli`는 LLM 실행 파일(`agy`, `claude`, `codex`, `cursor-agent`, `copilot`)만 선택합니다.

| 실습 | 산출물 |
| --- | --- |
| A | rules.dl, S1_result.json |
| B | S2_result.json, S3_result.json, comparison.csv, delta_actual.txt |

## 실습 A · 10분

```sh
python3 run_lesson5.py --task reason
```

`rules.dl`에서 직접 호출을 reach에 넣는 첫 규칙과 경로를 확장하는 재귀 규칙을 확인합니다. S1의 직접 관계는 3개, reach는 6개, candidate는 3개, candidate_doc은 3개입니다. `S1_result.json`의 paths에서 shop의 F01/F02/F03 경로를 원문과 대조합니다. 경로 설명은 Python에서 구성한 별도 근거 계층입니다.

## 실습 B · 13분

```sh
python3 run_lesson5.py --task compare
python3 run_lesson5.py --task delta
```

앞 8분은 `raw/CHG-12_v1.md`와 세 결과를 비교합니다.

| 스냅샷 | 의미 | 직접 관계 | reach | 후보 | 관련 문서 튜플 |
| --- | --- | --- | --- | --- | --- |
| S1 | 기준 구성 | 3 | 6 | shop, order, pay | 3 |
| S2 | order의 ledger 직접 조회 가정 추가 | 4 | 6 | shop, order, pay | 3 |
| S3 | S2에서 pay의 ledger 직접 호출 제거 | 3 | 5 | shop, order | 1 |

S2/S3는 설계 검증 가정이며 운영 배포 사실이 아닙니다. 후반 5분은 `session_delta.py`의 실제 이벤트을 확인합니다. friend/mutual 예제의 step 1은 + 두 줄, step 2는 변화 없음, step 3은 - 두 줄입니다. 서비스 스냅샷 재실행과 같은 세션 갱신을 구분하여 `delta_review.md`에 설명합니다.

`session_delta.py`가 하나의 `EasySession`에서 `insert`, `remove`, `step`을 실행합니다. 실제 이벤트가 +2/0/−2인지 확인하고 `delta_run.json`에 기록합니다.

## 확인 문제

- S3에는 order → ledger가 남아서 order와 shop 후보도 남습니다.
- 후보는 점검 대상입니다. 실제 장애 여부는 현재 지표로 확인합니다.

6교시는 S2/S3가 아닌 **S1으로 복귀**합니다.

## 실행 기록과 제출

LLM 실행은 실제 입력·stdout·stderr·상태를 runs/에 남깁니다. `--overwrite`는 기존 LLM 결과를 백업한 뒤 교체합니다. 실패·빈 응답·시간 초과는 성공 결과로 대체하지 않습니다. Datalog 실행은 입력과 실제 엔진 출력을 저장하며 이전 결과도 백업합니다.

[최종 교육자료의 해설](reference/ANSWER.md)은 실습 후 비교용입니다. `review.md`에는 본인의 실제 검토를 기록하세요. 모든 원문은 교육용 합성 사례입니다.
