# BF5 Advanced Input Reliability Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 목적

BF5는 `secondary_harvest`를 더 많이 직접 쓰는 단계가 아니라, 이미 들어오는 advanced collector 입력을 `얼마나 믿어도 되는지` 먼저 요약하는 단계다.

핵심 질문은 아래와 같다.

- `tick_flow`는 살아 있는데 `order_book`은 거의 비어 있을 때 어떻게 읽을 것인가
- `event_risk`가 살아 있으면 wait/cut 판단에 어느 정도 반영할 것인가
- secondary input을 raw로 과신하지 않으면서도 살아 있는 collector는 버리지 않도록 만들 수 있는가

## 2. 왜 BF5가 필요한가

SF2와 SF5 결론은 아래와 같았다.

- `tick_state_active_like_ratio`와 `event_risk_state_active_like_ratio`는 높다
- `order_book_state_active_like_ratio`는 매우 낮다
- broad raw add는 우선순위가 아니다
- `secondary_harvest direct-use gap`은 여전히 남아 있다

즉 지금 병목은 `raw가 없다`가 아니라, `advanced collector availability를 해석 가능한 bridge로 바꾸지 못한다`는 점이다.

## 3. BF5의 역할

BF5는 아래 두 축을 동시에 만족해야 한다.

1. `order_book`이 비어 있다고 해서 advanced context 전체를 0으로 만들지 않는다.
2. `order_book`이 비어 있는 상태에서 collision 판단을 과신하지 않는다.

즉 BF5는 `믿을 만한 advanced context는 살리고`, `비어 있는 collector는 따로 감쇠`하는 bridge다.

## 4. 입력

BF5는 주로 `state_vector_v2.metadata`의 아래 값을 읽는다.

- `advanced_input_activation_state`
- `tick_flow_state`
- `order_book_state`
- `event_risk_state`

## 5. 출력 shape

BF5 bridge summary는 아래를 고정한다.

- `advanced_reliability`
- `order_book_reliable`
- `event_context_reliable`

component score에는 아래를 남긴다.

- `activation_score`
- `tick_context_reliable`
- `event_context_available`
- `event_context_reliable`
- `event_caution`
- `order_book_available`
- `order_book_reliable`
- `order_book_gap_penalty`
- `advanced_positive`

## 6. 연결 대상

### transition forecast

BF5는 transition branch에서 `BF1 false_break_risk`를 얼마나 믿을지 조정한다.

### trade management forecast

BF5는 management branch에서 아래 bridge의 유효 강도를 보정한다.

- `BF3 management_fast_cut_risk_v1`
- `BF4 trend_continuation_maturity_v1`

즉:

- advanced reliability가 높으면 BF3/BF4를 조금 더 믿는다
- order book이 비면 collision 쪽만 따로 약하게 본다
- event context가 살아 있으면 event caution 쪽은 별도 scale로 반영한다

## 7. 계약 원칙

- BF5는 `secondary owner`가 아니다
- raw `tick/order_book/event`를 직접 chart owner나 action owner로 만들지 않는다
- BF5는 어디까지나 `modifier`다

## 8. 완료 기준

1. `forecast_features`에 BF5 summary가 노출된다
2. transition/management metadata에 BF5 trace가 남는다
3. `semantic_forecast_inputs_v2_usage_v1`에서 secondary usage가 branch math direct-use로 표시된다
4. management version이 BF5 반영 버전으로 올라간다
5. 테스트와 usage audit fixture가 새 계약을 통과한다

## 9. 다음 단계

BF5 다음 active step은 `BF6 detail_to_csv_activation_projection_v1`이다.
