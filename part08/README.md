# 8교시 · 근거 있는 답변 생성과 위키 업데이트

S1b 결과와 문맥 근거로 답변을 쓰고 분석 위키·연결·변경 기록을 생성합니다.

실습 A는 10분, 실습 B는 13분 동안 진행합니다.

## 바로 실행

프로젝트 루트에서 `python3 -m pip install -r demos/requirements.txt`와 `python3 demos/setup_pyrewire.py`로 PyreWire 1.1.2 이상을 준비한 뒤 실행합니다.

```sh
cd demos/part08
python3 run_lesson8.py --cli agy --task all --overwrite
```

CPython 3.11~3.14와 `pyrewire>=1.1.2`를 사용합니다. 엔진은 `EasySession.snapshot()`을 직접 호출합니다. 6~8교시의 `--cli`는 LLM 실행 파일(`agy`, `claude`, `codex`, `cursor-agent`, `copilot`)만 선택합니다.

| 실습 | 산출물 |
| --- | --- |
| A | S1b_result.json, evidence_bundle.json, final_answer.md, claim_review.csv |
| B | wiki/analysis/ledger-impact-S1b.md, change.diff, change_review.md, wiki/log.md |

## 준비: 앞 교시 결과 연결

6교시 `evidence_bundle.json`이 필요합니다. 7교시 `S1b_input.json`이 있으면 이를 읽고, 없으면 최종 교육자료의 S1b 승인 체크포인트를 사용합니다. S1b를 실제 Wirelog로 다시 조회하고 RUN-02 근거를 추가하여 이 폴더의 근거 묶음을 만듭니다.

## 실습 A · 10분

```sh
python3 run_lesson8.py --cli agy --task answer --overwrite
python3 run_lesson8.py --cli agy --task claims --overwrite
```

`answer`는 `prompt.txt`를 변환하는 작업이 아니라, 질문에 필요한 근거를 제공 문서에서 찾아 답변을 작성하는 작업입니다. `prompt.txt`에는 질문·근거 탐색 절차·출처 표기 규칙을 두고, 후보 이름·경로·수치·조치 조건은 입력 자료에서 찾아 쓰도록 합니다.

실행 스크립트는 S1b 질의를 다시 수행하고 근거 묶음을 준비한 뒤, `S1b_result.json`, `S1b_input.json`, `evidence_bundle.json`, `raw/*.md`의 내용을 LLM 입력에 함께 넣습니다. LLM은 질의 결과의 후보와 사실 ID를 출처에 연결하고, 관련 문서 참조를 따라 입력에 포함된 원문에서 설계 이유·업무 영향·과거 관측·운영 조건·담당을 찾아 `final_answer.md` 본문을 작성합니다. 원문 파일은 스크립트가 읽으며, CLI의 파일 검색 도구나 웹 검색을 사용하는 방식은 아닙니다. 입력에 기존 `final_answer.md`나 `reference/ANSWER.md`는 포함하지 않습니다.

화면에는 참고 파일 경로와 CLI 진행 상태가 표시됩니다. 실제 전달한 문서는 안내된 `runs/.../input.txt`에서 확인할 수 있습니다. LLM 호출 없이 입력 구성을 확인하려면 `python3 run_lesson8.py --cli agy --task answer --overwrite --dry-run`을 실행하세요. 미리보기는 기존 질의 결과와 근거 파일을 사용하며 S1b 질의와 근거 준비를 다시 수행하지 않습니다.

4분 동안 답변을 읽고, 3분 동안 각 문장을 원문 사실·규칙 결론·제안·현재 미확인으로 분류하고, 3분 동안 동료와 원문·경로를 대조합니다. `claim_review.csv`는 LLM 검토 제안입니다. 현재 승인 여부나 검토자를 자동으로 만들지 않습니다.

확인할 내용은 후보 4개, S1b/candidate-v1, 사실 ID 경로, notify의 알림 영향, 186/4,900건의 확정 지연, 과거 25분·42분, OPS-04의 조건·범위·건별 승인입니다.

## 실습 B · 13분

```sh
python3 run_lesson8.py --cli agy --task wiki --overwrite
python3 run_lesson8.py --cli agy --task review --overwrite
python3 check_links.py wiki
```

5분 동안 분석 페이지를 검토하고, 4분 동안 서비스·원문·index 링크를 따라가고, 4분 동안 `change.diff`와 `wiki/log.md`를 확인합니다. 시작 위키는 최종 교육자료의 1교시 완료 예시입니다. 원문은 보존하며 변경 전 파일은 runs/에 백업합니다.

분석 페이지와 로그는 **사람 검토 대기**로 저장합니다. 수강생이 실제 원문·경로·링크와 diff를 확인한 뒤 검토자·일자를 기록합니다. 근거가 부족한 제안은 그대로 대기 목록에 둡니다.

## 확인 문제

notify는 F04/F02/F03과 RUN-02의 발송 보류·격리 설명을 함께 제시합니다. 25분은 과거 관측이고 OPS-04의 승인은 절차 승인입니다. 현재 사고의 실행 조건·승인과 향후 복구는 추가 확인이 필요합니다.

최종 제출은 답변, 주장표, S1b 질의 결과, 근거 묶음, 위키, 실제 변경 diff와 실행 로그입니다.

## 실행 기록과 제출

LLM 실행은 실제 입력·stdout·stderr·상태를 runs/에 남깁니다. `--overwrite`는 기존 LLM 결과를 백업한 뒤 교체합니다. 실패·빈 응답·시간 초과는 성공 결과로 대체하지 않습니다. Datalog 실행은 입력과 실제 엔진 출력을 저장하며 이전 결과도 백업합니다.

[최종 교육자료의 해설](reference/ANSWER.md)은 실습 후 비교용입니다. `review.md`에는 본인의 실제 검토를 기록하세요. 모든 원문은 교육용 합성 사례입니다.
