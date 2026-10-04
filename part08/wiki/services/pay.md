# pay · 결제 서비스

상태: 정답 예시 / 구성 기준: ARCH-01 v1
운영 담당: 결제정산팀. [ARCH-01 v1 §3](../../raw/ARCH-01_v1.md)

PG 승인 응답 뒤 ledger POST /v1/journal-entries를 동기로 호출한다. 제한 시간은 1.8초다. 시간 초과 시 LEDGER_PENDING을 남긴다. 시간 초과는 승인 실패 확정과 다르다. [ARCH-01 v1 §2](../../raw/ARCH-01_v1.md)
INC-03에서는 영향 가맹점의 대사 큐 소비만 승인 후 일시 정지했다. PG 전체 차단으로 요약하지 않는다. [INC-03 v1 §2](../../raw/INC-03_v1.md)

관련: [order](order.md), [사고 기록](../incidents/INC-03.md).
미확인: 현재 사고에서 OPS-04의 진입 조건이 충족되었는지 여부. ADR-07 §3이 연결한 절차 원문은 후속 검색에서 확인한다.

- [ledger 영향 분석](../analysis/ledger-impact-S1b.md) — S1b / 검토 대기
