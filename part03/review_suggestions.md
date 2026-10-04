# LLM 검토 제안 — 사람 검토 전

> **안내**: 본 검토 제안서는 `assertions.jsonl` (F01~F03) 및 `error_candidates.json` (E01~E06) 추출 결과를 승인된 원문 문서와 대조 분석하여 작성한 LLM 자동 제안서입니다. 본 권고 판정(`approved`, `rejected`, `held`)은 자동화 검토 제안일 뿐이며 사람의 실제 최종 승인과 엄격히 구분됩니다. `review.csv` 및 `approved.jsonl`의 수정이나 실제 검토자·검토 일자 표기는 포함하지 않습니다.

---

## 1. 추출 항목 및 오류 후보 검토 제안

| ID | 주장 | 권고 판정 | 원문 근거 | 수정 또는 보류 이유 |
| --- | --- | --- | --- | --- |
| F01 | shop depends_on order | approved | [raw/ARCH-01_v1.md](raw/ARCH-01_v1.md) (ARCH-01 v1 §1) | 원문 인용구("쇼핑몰 서버(shop)는 주문서가 접수되면 주문 서비스(order)의 POST /v1/orders를 호출한다.")가 정확히 일치함. `shop`(Service)과 `order`(Service) 간 직접 HTTP 호출이며 승인된 운영 기준의 의존성이므로 승인 제안함. |
| F02 | order depends_on pay | approved | [raw/ARCH-01_v1.md](raw/ARCH-01_v1.md) (ARCH-01 v1 §1), [raw/ADR-07_v1.md](raw/ADR-07_v1.md) (ADR-07 v1 §1) | 원문 인용구("주문 서비스(order)는 재고 예약과 견적 유효기간을 확인한 뒤 결제 서비스(pay)의 POST /v1/payments/authorize를 호출한다.")가 정확히 일치함. `order`(Service)와 `pay`(Service) 간 직접 HTTP 호출이며 승인된 운영 기준의 의존성이므로 승인 제안함. |
| F03 | pay depends_on ledger | approved | [raw/ARCH-01_v1.md](raw/ARCH-01_v1.md) (ARCH-01 v1 §2) | 원문 인용구("결제 서비스(pay)는 PG사의 승인 응답을 받은 뒤 원장 서비스(ledger)의 POST /v1/journal-entries를 동기로 호출한다.")가 정확히 일치함. 현재 운영 승인 기준인 ARCH-01 v1의 동기 HTTP 직접 호출에 부합하므로 승인 제안함. |
| E01 | ledger depends_on pay | rejected | [raw/ARCH-01_v1.md](raw/ARCH-01_v1.md) (ARCH-01 v1 §2) | **호출 방향 오류.** 원문상 `pay`가 `ledger`를 호출하므로 의존 방향은 `pay depends_on ledger`임. 방향이 반대로 잘못된 주장이므로 반려하며, E 후보를 그대로 승인 사실에 반영하지 않음. |
| E02 | pay 담당 팀 Platform | rejected | [raw/ARCH-01_v1.md](raw/ARCH-01_v1.md) (ARCH-01 v1 §3) | **운영 담당 팀 명칭 오류.** 원문에 명시된 `pay`(결제 서비스)의 운영 담당 팀은 `결제정산팀`임. 주장을 반려하며 `pay owned_by 결제정산팀`으로 수정 필요. |
| E03 | shop depends_on ledger 직접 호출 | rejected | [raw/ARCH-01_v1.md](raw/ARCH-01_v1.md) (ARCH-01 v1 §1·§2), [ontology/relations.csv](ontology/relations.csv) | **간접 경로 및 직접 호출 오류.** 원문 아키텍처는 `shop` → `order` → `pay` → `ledger` 흐름으로 `shop`과 `ledger` 간 직접 HTTP 호출이 없음. ontology 규칙상 간접 호출 경로는 `depends_on` 대상에서 제외되므로 주장을 반려함. |
| E04 | pay 원장 호출 제거 완료 | rejected | [raw/ARCH-01_v1.md](raw/ARCH-01_v1.md) (ARCH-01 v1 §2), [raw/ARCH-01_v2.md](raw/ARCH-01_v2.md) (ARCH-01 v2 §1) | **문서 버전 및 운영 적용 상태 불일치.** 원장 호출 제거(비동기 전환)는 [raw/ARCH-01_v2.md](raw/ARCH-01_v2.md)(상태: 검토 중, 운영 미반영)의 검토안일 뿐임. 현재 승인 완료된 운영 기준([raw/ARCH-01_v1.md](raw/ARCH-01_v1.md) §2)은 동기 호출을 유지하므로 주장을 반려함. |
| E05 | ledger-db = ledger Service | rejected | [raw/GLOSS-01_v1.md](raw/GLOSS-01_v1.md) (GLOSS-01 v1 §1), [ontology/types.csv](ontology/types.csv), [entities.json](entities.json) | **개체 타입 동일시 오류.** `ledger`는 `Service` 타입(원장 서비스)이고 `ledger-db`는 `DataStore` 타입(원장 데이터베이스)으로 서비스 그래프에서 제외되는 별개 개체임. 동일 개체 주장이므로 반려함. |
| E06 | payment와 pay 별도 서비스 | rejected | [raw/GLOSS-01_v1.md](raw/GLOSS-01_v1.md) (GLOSS-01 v1 §1), [aliases.json](aliases.json) | **명시적 별칭 오인.** 원문 GLOSS-01 v1 §1에 "결제 서비스의 공식 ID는 pay이며, 기존 문서의 payment도 같은 서비스를 가리킨다."라고 명시됨. 별도 서비스가 아닌 명시적 별칭(alias) 관계이므로 주장을 반려함. |

---

## 2. 현재 운영 사실과 검토 중 설계 변경의 분리

| 구분 | 문서 번호 및 버전 | 문서 상태 | 주요 내용 및 호출 구조 |
| --- | --- | --- | --- |
| **현재 운영 기준** | [raw/ARCH-01_v1.md](raw/ARCH-01_v1.md) (ARCH-01 v1) | **승인 완료** (운영 배포 2026-08-12 기준) | 결제 서비스(`pay`)가 PG 승인 응답 후 원장 서비스(`ledger`)의 `POST /v1/journal-entries`를 **동기(1.8초 타임아웃)**로 직접 호출함. |
| **검토 중 설계 변경** | [raw/ARCH-01_v2.md](raw/ARCH-01_v2.md) (ARCH-01 v2) | **검토 중** (운영 미반영, 배포 일정 미정) | `pay`가 `ledger`를 직접 호출하지 않고 결제 승인 이벤트를 발행하는 **비동기 기록 방식** 검토 중. 현재 운영 환경에는 미반영됨. |

---

## 3. 메타데이터 파일(`aliases.json`, `entities.json`)의 원문 불일치 사항

### 3.1 `aliases.json` 불일치 및 누락
1. **배포 리소스 명칭 별칭 누락**:
   - [raw/GLOSS-01_v1.md](raw/GLOSS-01_v1.md) (GLOSS-01 v1 §1) 본문에 "배포 리소스 이름은 `payment-api`다."라고 기술되어 있으나, `aliases.json`에는 `payment-api` (canonical_id: `pay`) 별칭 항목이 누락되어 있음.
2. **인용구 출처 및 표기 방식 불일치**:
   - `aliases.json`에서 `결제 서비스` 별칭의 quote로 본문 문장("결제 서비스의 공식 ID는 pay이며...")이 지정되어 있으나, 원문 [raw/GLOSS-01_v1.md](raw/GLOSS-01_v1.md) (GLOSS-01 v1 §1) 용어 표의 `| pay / payment | 결제 서비스 |` 행 인용 방식과 일치하지 않음.

### 3.2 `entities.json` 불일치 및 누락
1. **서비스 개체 추출 누락**:
   - [raw/GLOSS-01_v1.md](raw/GLOSS-01_v1.md) (GLOSS-01 v1 §1) 표에 알림 워커(`notify`)가 명시되어 있고 `aliases.json`에도 수록되어 있으나, `entities.json`의 `services` 목록 및 `excluded_from_service_graph` 목록 전체에서 `notify` 개체가 제외/누락됨.
2. **API 출처 절 번호(section) 단일화 불일치**:
   - `entities.json`의 `api:order:POST:/v1/orders` 항목 출처가 `§2`로 지정되어 있으나, 해당 API의 직접 호출 관계(`shop` → `order`)는 [raw/ARCH-01_v1.md](raw/ARCH-01_v1.md) (ARCH-01 v1 §1)에 작성되어 있으며 §2는 타임아웃 정보 표임. 호출 흐름과 타임아웃 출처 절을 분리하거나 정확히 병기할 필요가 있음.
