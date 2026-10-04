# 5교시 정답 해설

한빛MRO 합성 문서 기반 예시입니다. 실제 검토자·일자는 수강생이 기록합니다. 문구가 달라도 근거·범위·상태가 같으면 됩니다.

## PPT 11: 실습 A 확인: 후보와 문서

문서 관계와 후보 관계를 결합한 결과입니다.

| 후보 | 관련 문서 | ledger까지의 경로 |
| --- | --- | --- |
| shop | 현재 about 입력에는 없음 | shop, order, pay, ledger |
| order | ADR-07:v1 | order, pay, ledger |
| pay | ARCH-01:v1 | pay, ledger |
| pay | INC-03:v1 | pay, ledger |

## PPT 13: 실습 B 확인: 대체 경로

설계 비교 결과에 시나리오 상태를 표시합니다.

| 스냅샷 | 분석 변경 | reach 수 | 후보 |
| --- | --- | --- | --- |
| S1 | 기준 구성 | 6 | shop, order, pay |
| S2 | order의 ledger 조회 추가 | 6 | shop, order, pay |
| S3 | pay의 직접 호출 제거 | 5 | shop, order |

## PPT 16: 확인 문제 해설

관계 계산의 결과와 운영 상태의 판단을 분리합니다.

### 질문 1의 답

order→ledger 직접 경로가 남으므로
order와 shop 후보를 유지합니다.

### 질문 2의 답

실제 중단을 단정할 수 없습니다.
의존 경로가 있으므로 점검 대상입니다.
운영 지표와 대응 문서를 추가 확인합니다.
