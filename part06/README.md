# 6교시 · 추론 결과를 확장하는 LLM 검색

S1으로 복귀하여 원문에서 설계 이유·조치 조건·관측 시간의 의미를 보완합니다.

실습 A는 10분, 실습 B는 13분 동안 진행합니다.

## 바로 실행

이 저장소의 루트(`requirements.txt`가 있는 폴더)에서 가상환경을 활성화하고 의존성을 준비한 뒤 실행합니다. `.venv`가 없으면 먼저 `python3 -m venv .venv`로 생성하세요. 패키지를 설치한 Python과 데모를 실행하는 Python이 같아야 합니다.

```sh
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 setup_pyrewire.py
cd part06
python3 run_lesson6.py --cli agy --task all --overwrite
```

이미 준비된 가상환경을 활성화하지 않고 실행하려면 `part06`에서 `../.venv/bin/python run_lesson6.py --cli agy --task all --overwrite`를 사용합니다. `agy`는 설치 및 로그인이 필요합니다.

CPython 3.11~3.14와 `pyrewire>=1.1.2`를 사용합니다. 엔진은 `EasySession.snapshot()`을 직접 호출합니다. 6~8교시의 `--cli`는 LLM 실행 파일(`agy`, `claude`, `codex`, `cursor-agent`, `copilot`)만 선택합니다.

| 실습 | 산출물 |
| --- | --- |
| A | S1_result.json, input.json, evidence_bundle.json |
| B | comparison.csv, search_plan.md |

## 실습 A · 10분

```sh
python3 run_lesson6.py --cli agy --task evidence --overwrite
```

S1을 실제 Wirelog로 조회하여 `input.json`을 만들고, 원문 4개를 LLM에 전달합니다. 2분 동안 후보·초기 문서를 확인하고, 4분 동안 생성된 근거를 읽고, 4분 동안 원문과 대조합니다.

`prompt.txt`는 질문·근거 탐색 절차·JSON 스키마를 제공합니다. 후보와 초기 문서는 `input.json`에서 읽고, 확장 문서는 원문의 참조를 따라 찾으며, 관측 수치·근거 절·조치 조건은 문서에서 추출합니다. 프롬프트에 이 값들의 정답을 미리 지정하지 않습니다. 파일 내용은 스크립트가 입력에 포함하며 CLI의 파일 검색 도구나 웹 검색을 사용하는 방식은 아닙니다. 기존 `evidence_bundle.json`과 정답 해설은 `evidence` 단계의 LLM 입력에 포함하지 않습니다.

생성 후에는 교육용 기대 후보·문서 집합·필수 근거 절과 원문 인용을 검사합니다. 이 검사는 LLM에 전달하는 지시와 별개이며, 의미의 정확성과 실제 적용 여부는 사람이 검토해야 합니다. 전달된 내용은 `runs/.../input.txt`에서 확인할 수 있습니다. `--dry-run`은 기존 `input.json`과 원문으로 입력만 만들며 질의를 다시 실행하지 않습니다.

`input.json`의 `candidate_doc`은 질의 결과의 `[서비스 ID, 문서 ID]` 연결을 그대로 전달합니다. 원문에서 서비스를 언급하는 것과 초기 about 연결이 있는 것은 구분합니다. 이전 버전의 `input.json`에 이 필드가 없으면 `--task evidence` 또는 `--task all`로 다시 생성하세요.

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

비교 프롬프트의 A/B/C는 검토 대상 주장입니다. 판정과 수치의 의미는 원문에서 확인하며, 검색 기록도 초기 문서 수나 확장 경로를 미리 정하지 않고 입력 자료에서 찾아 작성합니다.

## 확인 문제

OPS-04 문서 승인과 현재 사고의 실행 승인은 별개입니다. 25분은 신규 주문 처리 정상화, 42분은 지연 주문 대사 완료입니다. 현재 지표·불일치 목록·영향 범위·승인 기록·향후 복구 시각은 제공되지 않았습니다.

7교시는 이 문맥에 RUN-02를 추가하고, 8교시는 실제 `evidence_bundle.json`을 읽습니다.

## 실행 기록과 제출

LLM 실행은 실제 입력·stdout·stderr·상태를 runs/에 남깁니다. `--overwrite`는 기존 LLM 결과를 백업한 뒤 교체합니다. 실패·빈 응답·시간 초과는 성공 결과로 대체하지 않습니다. Datalog 실행은 입력과 실제 엔진 출력을 저장하며 이전 결과도 백업합니다.

[최종 교육자료의 해설](reference/ANSWER.md)은 실습 후 비교용입니다. `review.md`에는 본인의 실제 검토를 기록하세요. 모든 원문은 교육용 합성 사례입니다.
