# order · 주문 서비스

상태: 정답 예시 / 구성 기준: ARCH-01 v1
운영 담당: 커머스플랫폼팀. [ARCH-01 v1 §3](../../raw/ARCH-01_v1.md)

shop의 주문 요청을 받고 pay의 POST /v1/payments/authorize를 호출한다. 승인 결과가 확정되기 전 PAYMENT_PENDING을 유지한다. [ARCH-01 v1 §1·§2](../../raw/ARCH-01_v1.md)
동기 승인 결정은 미승인 출고와 중복 승인 가능성을 줄이기 위한 것이다. 즉시 확정 후 보상하는 대안은 이번 범위에서 채택하지 않았다. [ADR-07 v1 §1·§2](../../raw/ADR-07_v1.md)

관련: [pay](pay.md), [원장 지연 사고](../incidents/INC-03.md).
미확인: 현재 당직자, 현재 지연·결제 상태.

- [ledger 영향 분석](../analysis/ledger-impact-S1b.md) — S1b / 검토 대기
