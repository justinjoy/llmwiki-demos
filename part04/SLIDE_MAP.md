# 4교시 슬라이드와 데모 연결

[데모에 맞춘 배포 슬라이드](../../slides/part04.pptx)

기준: `04_Datalog_모델링과_Wirelog_연결_v4.pptx`의 18장과 발표자 노트. 슬라이드 원본은 수정하지 않습니다.

| 슬라이드 | 제목 | 실습 자료와 확인할 작업 |
| --- | --- | --- |
| 1 | Datalog 모델링과 | README.md의 목표·입력 범위 확인 |
| 2 | 학습 목표와 60분 진행 | README.md의 목표·입력 범위 확인 |
| 3 | 온톨로지의 실행 모델 투영 | S1.json·--assertions의 입력 구분, input.json의 근거와 고정 about 링크 |
| 4 | Datalog의 기본 요소 | 원문·데이터 구조·규칙의 의미 확인 |
| 5 | 기본 관계와 질의 규칙 | 원문·데이터 구조·규칙의 의미 확인 |
| 6 | 승인 사실 적재 | 매 실행 facts.dl 생성, part03 승인 DB·메타데이터 및 최신 판정 검증 |
| 7 | Python과 Wirelog의 연결 방식 | 원문·데이터 구조·규칙의 의미 확인 |
| 8 | 시연: Python에서 질의 실행 | shared/query.py의 evaluate()를 실제 호출하고 direct·pay_doc 확인 |
| 9 | 설치와 실행 준비 | setup_pyrewire.py, run_lesson4.py --task all, 매 실행 --assertions 선택 |
| 10 | 실습 A: 직접 관계 조회 | 실습 A: 제공 model.dl과 S1 입력, 생성 input.json·facts.dl·lesson.dl·result.json |
| 11 | 실습 A 확인: 결과 집합 | 실습 A 결과와 reference/ANSWER.md 대조 |
| 12 | 실습 B: 질의 변경과 입력 검증 | 실습 B: queries.dl, extended_result.json, invalid_result.json, direction_result.json |
| 13 | 실습 B 확인: 선언과 질의 | 기본 S1 추가 결과, expected_error 열 수 오류와 success 역방향 결과 비교 |
| 14 | 실행 오류의 진단 순서 | 일반 engine 로그와 invalid 실습 산출물 구분, 재검토 입력 차단 |
| 15 | 확인 문제 | README.md 확인 문제·원문 근거 설명 |
| 16 | 확인 문제 해설 | 새 세션·방향 검증, 빈 결과는 success이며 relations에서 생략 |
| 17 | 실행 모델과 다음 단계 | 실제 결과·검토 기록·다음 교시 입력 제출 |
| 18 | LLMWiki와 Wirelog 실습 과정 | 실제 결과·검토 기록·다음 교시 입력 제출 |
