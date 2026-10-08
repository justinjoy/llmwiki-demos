# 4교시 정답 해설

한빛MRO 합성 문서 기반 예시입니다. 실제 검토자·일자는 수강생이 기록합니다. 문구가 달라도 근거·범위·상태가 같으면 됩니다.

## 실습 A 확인: 결과 집합

결과의 순서 대신 튜플 집합을 비교합니다.

| 관계 | 예상 튜플 | 의미 |
| --- | --- | --- |
| direct | ("shop", "order") | shop의 직접 의존 |
| direct | ("order", "pay") | order의 직접 의존 |
| direct | ("pay", "ledger") | pay의 직접 의존 |
| pay_doc | ("ARCH-01:v1") | 구조 설명 문서 |
| pay_doc | ("INC-03:v1") | 장애 기록 문서 |

## 실습 B 확인: 선언과 질의

스키마 검사가 의미의 방향까지 검증하지는 않습니다.

```text
.decl order_doc(doc: symbol)
.decl shop_dep(dst: symbol)
order_doc(D) :- about(D, "order").
shop_dep(Y) :- depends_on("shop", Y).

// 기대 집합
// order_doc: { "ADR-07:v1" }
// shop_dep:  { "order" }
```

## 확인 문제 해설

연동 방식과 데이터 의미를 정확하게 설명하는 것이 목표입니다.

### 질문 1의 답

새 EasySession을 열면 새 평가입니다.
세션 내 추가·철회와 구분합니다.

### 질문 2의 답

타입만으로 구분하기 어렵습니다.
관계 사전과 원문을 대조해야 합니다.
