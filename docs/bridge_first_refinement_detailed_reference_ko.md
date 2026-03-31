# Bridge-First Refinement Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 `state / forecast validation (SF0~SF6)` 결과를 받아
다음 구현 본선을 `bridge-first refinement (BF)`로 여는 기준 문서다.

BF의 목적은 새 raw field를 크게 더하는 것이 아니다.
이미 존재하는

- `State`
- `Evidence`
- `Belief`
- `Barrier`
- `Forecast`

를 그대로 owner로 뒤섞지 않고,
`product acceptance`와 `forecast branch/value path`가 함께 쓸 수 있는
작은 bridge summary surface로 다시 묶는 것이다.

즉 BF는 아래 한 줄로 이해하면 된다.

```text
raw를 더 많이 넣는 단계가 아니라,
이미 있는 고차 입력을 chart/wait/entry/hold/exit와 forecast가 함께 읽을 수 있는 bridge로 재구성하는 단계
```

## 2. 왜 BF가 필요한가

SF6 close-out 기준 공식 결론은 아래였다.

- `broad raw add`: 보류
- `broad secondary raw expansion`: 보류
- `broad collector rebuild`: 보류
- `forecast threshold tuning first`: 보류
- 단일 next action: `product_acceptance_common_state_aware_display_modifier_v1`

이 결론의 배경은 다음과 같다.

### 2-1. raw surface는 이미 넓다

- `StateRawSnapshot` 39개
- `StateVectorV2` 17개
- `ForecastFeaturesV1` 11개
- `forecast harvest` 4섹션 34개

그리고 SF1 기준 `state_vector`, `forecast_features`, `state_harvest`, `secondary_harvest`는
거의 항상 존재했다.

즉 지금 문제는 `입력이 없다`가 아니다.

### 2-2. activation은 일부만 문제다

SF2 기준:

- `tick_state_active_like_ratio ≈ 0.8997`
- `event_risk_state_active_like_ratio ≈ 0.8997`
- `order_book_state_active_like_ratio ≈ 0.0003`

즉 collector 전체가 죽은 것이 아니라
`order_book`만 targeted availability gap으로 보는 것이 더 맞다.

### 2-3. usage / value path가 더 큰 병목이다

SF3 기준:

- `secondary_harvest_direct_use_field_count = 0`

SF4 기준:

- `p_false_break separation_gap = -0.0147`
- `p_continue_favor separation_gap = 0.0475`
- `p_fail_now separation_gap = 0.0055`

즉 이미 들어오는 입력이 있어도
그 입력이 transition/management 의미 차이를 충분히 만들지 못하고 있다.

### 2-4. 그래서 bridge가 먼저다

BF는 아래 문제를 해결하려고 열린다.

- `WAIT / act` 구분이 평평함
- `hold / cut` 구분이 약함
- chart/product acceptance와 forecast가 같은 고차 의미를 공유하지 못함
- secondary activation이 살아도 direct-use/value path가 열리지 않음

## 3. BF의 핵심 원칙

### 3-1. owner와 modifier를 섞지 않는다

- `scene`은 여전히 scene owner다
- `State / Evidence / Belief / Barrier / Forecast bridge`는 modifier다

즉 chart나 entry에서
`이 자리가 어떤 장면인가`는 scene이 정하고,
`지금 시장 힘에서 얼마나 세게/약하게 보여줄 것인가`는 bridge가 정한다.

### 3-2. raw를 직접 노출하지 않는다

BF는 raw detector나 raw forecast payload를 consumer/chart owner처럼 직접 노출하지 않는다.
대신 다음처럼 요약된 bridge만 만든다.

- `act_vs_wait_bias`
- `false_break_risk`
- `awareness_keep_allowed`
- `hold_reward_hint`
- `fast_cut_risk`
- `continuation_maturity`
- `advanced_reliability`

### 3-3. forecast와 product acceptance가 함께 쓴다

BF는 forecast 내부 branch math만을 위한 레이어가 아니다.
같은 bridge가 아래를 같이 도와야 한다.

- transition forecast refinement
- trade management forecast refinement
- chart wait awareness
- product acceptance의 `3/2/1/W/X` 재조정
- hold / exit 해석

즉 `예측용 따로`, `차트용 따로`를 만들지 않는다.

## 4. BF 전체 구조

```text
BF1. act_vs_wait_bias_v1
BF2. management_hold_reward_hint_v1
BF3. management_fast_cut_risk_v1
BF4. trend_continuation_maturity_v1
BF5. advanced_input_reliability_v1
BF6. detail_to_csv_activation_projection_v1
BF7. close-out and product/forecast handoff
```

## 5. BF1. act_vs_wait_bias_v1

### 목표

`WAIT / observe / directional act` 구분을 더 잘 드러내는 공통 bridge를 만든다.

### 왜 먼저인가

- `p_false_break`가 가장 flat하다
- transition forecast에 바로 들어간다
- chart wait awareness에도 바로 연결된다
- product acceptance의 `W / awareness`를 설명 가능한 방식으로 바꿀 수 있다

### 입력 레이어

- `state`
- `evidence`
- `belief`
- `barrier`

### 출력 후보

- `act_vs_wait_bias`
- `false_break_risk`
- `awareness_keep_allowed`

### 연결 대상

- `transition_forecast`
- `consumer_check_state`
- `entry_wait_state_bias_policy`
- product acceptance chart/wait review

## 6. BF2. management_hold_reward_hint_v1

### 목표

hold를 유지할 이유가 있는지, recoverability가 있는지를 bridge로 정리한다.

### 출력 후보

- `hold_reward_hint`
- `recoverability_hint`
- `continuation_tailwind`

### 연결 대상

- `trade_management_forecast`
- hold/exit acceptance

## 7. BF3. management_fast_cut_risk_v1

### 목표

빨리 끊길 가능성이 큰지, event/friction/collision 때문에 강한 hold를 하면 안 되는지를 bridge로 만든다.

### 출력 후보

- `fast_cut_risk`
- `collision_risk`
- `event_caution`

### 연결 대상

- `trade_management_forecast`
- exit caution / cut-now review

## 8. BF4. trend_continuation_maturity_v1

### 목표

trend slice에서 hold/continuation value가 왜 약한지 보완하는 trend 전용 bridge를 만든다.

### 출력 후보

- `continuation_maturity`
- `exhaustion_pressure`
- `trend_hold_confidence`

## 9. BF5. advanced_input_reliability_v1

### 목표

advanced collector가 실제로 믿을 만한지 요약해
secondary input을 raw로 과신하지 않게 만든다.

### 출력 후보

- `advanced_reliability`
- `order_book_reliable`
- `event_context_reliable`

## 10. BF6. detail_to_csv_activation_projection_v1

### 목표

detail 쪽 usage/activation trace와
CSV 쪽 value coverage를 이어주는 review bridge를 만든다.

이건 live decision bridge라기보다
analysis surface를 더 정확히 보는 보조 bridge다.

### 출력 후보

- `activation_slice_projection`
- `section_value_projection`

## 11. 주 대상 파일

BF에서 가장 자주 만지게 될 owner는 아래다.

- `backend/trading/engine/core/forecast_features.py`
- `backend/trading/engine/core/forecast_engine.py`
- `backend/services/context_classifier.py`
- `backend/services/entry_service.py`
- `backend/services/consumer_check_state.py`
- `backend/services/entry_wait_state_bias_policy.py`
- `backend/services/consumer_contract.py`

## 12. BF에서 하지 않을 것

아래는 BF 범위 밖이다.

- broad raw field expansion
- raw detector를 consumer/chart owner처럼 직접 노출
- order_book collector 전체 재설계
- threshold-only 튜닝으로 bridge/value path 문제를 우회
- semantic foundation 의미 변경

## 13. 완료 기준

BF close-out은 아래를 만족할 때 가능하다.

1. BF1~BF3 bridge가 forecast와 product acceptance 양쪽에 연결된다.
2. `WAIT / act`, `hold / cut` 차이가 이전보다 더 설명 가능해진다.
3. raw field를 더 늘리지 않고도 separation 개선 근거가 생긴다.
4. chart/product acceptance와 forecast refinement가 같은 bridge 언어를 쓴다.

## 14. 현재 단일 next action

지금 BF에서 바로 열어야 하는 건 아래다.

```text
BF7 close-out까지 완료했고,
다음 active handoff는 product_acceptance_common_state_aware_display_modifier_v1 이다.
```

한 줄 요약:

```text
BF는 raw를 더 넣는 트랙이 아니라,
이미 있는 상위 입력을 forecast와 product acceptance가 함께 쓸 bridge로 재구성하는 트랙이다.
```
