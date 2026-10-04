# LLM 변경 검토 제안 — 사람 검토 전

## 1. 개요

본 문서(`change_review.md`)는 S1b 스냅샷 기반의 `change.diff`, 현재 분석 페이지([wiki/analysis/ledger-impact-S1b.md](wiki/analysis/ledger-impact-S1b.md)), 답변([final_answer.md](final_answer.md)), 그리고 관련 업무 원문(`raw/*.md`)을 비교·검토하여 작성된 변경 검토 제안서입니다.

- **검토 대상 스냅샷 및 규칙**: S1b / `candidate-v1`
- **검토 대상 변경 파일**:
  - [wiki/analysis/ledger-impact-S1b.md](wiki/analysis/ledger-impact-S1b.md) (신규 분석 페이지 작성)
  - `wiki/index.md` (분석 페이지 목차 연결)
  - `wiki/log.md` (S1b 분석 초안 변경 이력 추가)
  - `wiki/services/order.md` (주문 서비스 페이지 연관 분석 링크 추가)
  - `wiki/services/pay.md` (결제 서비스 페이지 연관 분석 링크 추가)
- **현재 검토 상태**: LLM 초안 생성 완료, **사람 검토 대기** (실제 사람 검토 미수행, 임의 사람 승인 기록 없음)

---

## 2. 변경 사항 세부 검토

### 2.1 변경된 주장 및 원문 근거

`change.diff`를 통해 반영된 주요 분석 내용과 원문 근거는 다음과 같이 부합함을 확인했습니다.

1. **전파 경로 및 점검 대상 후보 도출**:
   - `ledger` 저장 지연 시 서비스 간 도달 가능성(reachability)에 따른 점검 대상 후보는 `notify`, `order`, `pay`, `shop` 4개 서비스입니다.
   - 이는 도달 가능성에 기반한 전파 후보일 뿐이며, 현재 실제 장애로 확정하는 것이 아닙니다.
   - `order` 서비스가 `pay` 서비스를 동기 호출하여 결제 완료를 확인한 뒤 주문을 확정하므로, `ledger` 지연 시 결제 및 주문 확정이 지연될 수 있습니다 ([ADR-07 v1 §1](raw/ADR-07_v1.md), [ADR-07 v1 §2](raw/ADR-07_v1.md), [ARCH-01 v1 §2](raw/ARCH-01_v1.md)).

2. **notify 알림 지연의 의미 및 처리 흐름**:
   - 알림 워커(`notify`)는 주문 완료 이벤트를 받으면 `order` 서비스의 상태 조회 API(`GET /v1/orders/{order_id}/status`)를 호출해 `CONFIRMED` 상태 확인 후 발송합니다 ([RUN-02 v1 §1](raw/RUN-02_v1.md), [RUN-02 v1 §3](raw/RUN-02_v1.md)).
   - 상태 조회 타임아웃 시 발송을 보류하고 재시도하며, 알림 오류로 주문 상태를 변경하거나 결제를 취소하지 않습니다 ([RUN-02 v1 §2](raw/RUN-02_v1.md)).

3. **과거 관측 기록 (INC-03) 해석**:
   - 장애 보고서([INC-03 v1](raw/INC-03_v1.md))의 186/4,900건은 2026-08-18 장애 발생 당시 전체 카드 결제 4,900건 중 186건의 주문 확정이 지연된 관측 수치입니다 ([INC-03 v1 §1](raw/INC-03_v1.md)).
   - 25분(신규 주문 처리 지연 지속 시간)과 42분(대사 완료 소요 시간)은 과거 사례의 관측치일 뿐, 향후 장애 복구 시간을 보장하는 기준이 아닙니다 ([INC-03 v1 §3](raw/INC-03_v1.md)).

4. **OPS-04 대사 작업 중지 조건 및 승인 절차**:
   - 원장 저장 타임아웃 5분 이상 지속 및 PG 승인 내역과 원장 기록 간 불일치 확인 시 대사 중지를 검토합니다 ([OPS-04 v1 §1](raw/OPS-04_v1.md)).
   - 결제정산팀 당직자와 장애 대응 책임자의 사전 승인을 받아 대상 가맹점(`merchant_id`)의 대사 큐 소비만 일시 중지하며, PG 승인 API 및 다른 가맹점 대사는 정상 운영합니다 ([OPS-04 v1 §1](raw/OPS-04_v1.md), [OPS-04 v1 §2](raw/OPS-04_v1.md)).

### 2.2 과잉 해석 교정 검증

[wiki/analysis/ledger-impact-S1b.md](wiki/analysis/ledger-impact-S1b.md) 및 [final_answer.md](final_answer.md)에 반영된 과잉 해석 교정 사항이 적절히 작성되었는지 검토했습니다.

- **`notify` 지연 교정**: `notify` 알림 지연은 결제 실패가 아니며, 알림 처리 오류가 주문 상태 변경이나 결제 취소를 일으키지 않도록 한다는 원문 범위로 구분했습니다.
- **`OPS-04` 조치 범위 교정**: 원장 지연 발생 시 전체 결제를 즉시 중단하는 것이 아니라, 진입 조건(5분 타임아웃 + 불일치 확인) 및 승인을 통해 영향 가맹점의 대사 큐만 국소 중지함을 밝혔습니다.
- **`INC-03` 관측 수치 교정**: 과거 25분/42분 수치가 미래의 복구 시간을 보장하지 않음을 명시했습니다.
- **장애 확정 교정**: Reachability 도출 후보가 실제 장애 확정이 아님을 명시했습니다.

### 2.3 서비스 및 Index 링크 구조 검토

`change.diff`의 위키 문서 간 연결 구조가 정상적인지 확인했습니다.

- `wiki/index.md`: 분석 페이지 목차 연결 (`- [ledger 영향 분석](analysis/ledger-impact-S1b.md) — S1b / 검토 대기`)
- `wiki/services/order.md`: 주문 서비스 문서 하단에 연결 (`- [ledger 영향 분석](../analysis/ledger-impact-S1b.md) — S1b / 검토 대기`)
- `wiki/services/pay.md`: 결제 서비스 문서 하단에 연결 (`- [ledger 영향 분석](../analysis/ledger-impact-S1b.md) — S1b / 검토 대기`)
- [wiki/analysis/ledger-impact-S1b.md](wiki/analysis/ledger-impact-S1b.md): 상단 탐색 입구 `[index](../index.md)` 및 후보 목록 내 서비스 링크(`[order](../services/order.md)`, `[pay](../services/pay.md)`) 구성 확인.

### 2.4 로그의 스냅샷 및 검토 상태 검토

`wiki/log.md` 및 분석 페이지 메타데이터의 기록 상태를 확인했습니다.

- **스냅샷 식별자**: `S1b`
- **적용 규칙**: `candidate-v1`
- **로그 내용**: `2026-10-03T15:50:57+09:00 · S1b 분석 초안` (생성: LLM CLI와 실행 스크립트, 상태: 사람 검토 대기)
- **검토자 및 일자**: "사람 검토 후 기록"으로 기재되어 임의 작성 방지 확인.

---

## 3. 안전성 및 투명성 검증

1. **잘못된 현재 장애 확정 여부**:
   - 현재 시점의 실장애 발생을 기정사실화하거나 단정하는 내용이 없으며, "S1b 스냅샷 기반의 전파 가능성 분석" 및 "과거 관측치"로만 서술되었습니다.

2. **임의 사람 승인 기록 여부**:
   - 실행 과정에서 실제 사람 검토가 이루어지지 않은 상태에 맞춰, 문서 상의 검토자/검토 일자가 모두 "사람 검토 후 기록"으로 표시되어 있습니다. 임의의 승인자 이름이나 승인 완결 기록이 존재하지 않습니다.

3. **현재 미확인 항목 명시**:
   - [wiki/analysis/ledger-impact-S1b.md](wiki/analysis/ledger-impact-S1b.md) §6 및 [final_answer.md](final_answer.md)에 따라 현재 지표, 불일치 여부, 영향 가맹점 목록, 실행 승인 기록, 향후 복구 시각, 현재 조건 충족 여부가 모두 **미확인** 상태로 투명하게 명시되어 있습니다.

---

## 4. 최종 제안 및 향후 절차

- **검토 결론**: 본 `change.diff` 변경안은 S1b 스냅샷 분석 결과와 원문 문서([ADR-07 v1](raw/ADR-07_v1.md), [ARCH-01 v1](raw/ARCH-01_v1.md), [INC-03 v1](raw/INC-03_v1.md), [OPS-04 v1](raw/OPS-04_v1.md), [RUN-02 v1](raw/RUN-02_v1.md)) 내용에 정확히 부합하며, 과잉 해석 방지 및 미확인 항목의 구분이 명확하게 이루어졌습니다.
- **향후 절차**:
  1. 실제 담당자(사람 검토자)가 [wiki/analysis/ledger-impact-S1b.md](wiki/analysis/ledger-impact-S1b.md)의 분석 내용 및 제안을 최종 검토합니다.
  2. 승인 완료 시 [wiki/analysis/ledger-impact-S1b.md](wiki/analysis/ledger-impact-S1b.md) 및 `wiki/log.md`의 검토자, 검토 일자, 검토 상태('검토 완료')를 업데이트합니다.
