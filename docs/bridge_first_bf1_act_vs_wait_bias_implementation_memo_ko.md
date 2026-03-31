# BF1 Act-vs-Wait Bias Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 목적

이 메모는 `BF1 act_vs_wait_bias_v1`의 첫 구현 패스를 코드/테스트 기준으로 닫기 위한 기록이다.

이번 구현의 목표는 아래 두 가지를 동시에 달성하는 것이었다.

- `transition_forecast`의 false-break / act-vs-wait discrimination을 더 설명 가능하게 만든다.
- `consumer_check_state`에서 soft-wait 장면이 완전 무표정하게 꺼지지 않도록 `awareness preserve` bridge를 연다.

즉 BF1은 forecast refinement 전용이 아니라, `forecast -> chart/product acceptance`를 같이 잇는 첫 bridge 구현이다.

## 2. 이번에 구현한 것

### 2-1. feature metadata에 BF1 bridge 추가

아래 파일에 BF1 bridge summary를 추가했다.

- [forecast_features.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/forecast_features.py)

이번 패스에서 새로 고정한 summary shape는 아래와 같다.

- `bridge_first_v1`
- `act_vs_wait_bias_v1`
  - `act_vs_wait_bias`
  - `false_break_risk`
  - `awareness_keep_allowed`
  - `component_scores`
  - `reason_summary`

이 bridge는 raw detector나 raw forecast payload를 그대로 쓰지 않고, 아래 레이어를 요약해서 만든다.

- `State`
- `Evidence`
- `Belief`
- `Barrier`

즉 owner를 바꾸지 않고 modifier를 만든 첫 단계다.

### 2-2. transition forecast에 BF1 blend 추가

아래 파일에 BF1 summary read helper와 blend를 추가했다.

- [forecast_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/forecast_engine.py)

이번 패스에서 실제로 한 일은 아래와 같다.

1. `features.metadata.bridge_first_v1.act_vs_wait_bias_v1`를 읽는 helper 추가
2. `false_break_pressure`에 BF1 `false_break_risk`를 약하게 additive blend
3. `bf1_act_vs_wait_bias`, `bf1_false_break_risk`, `bf1_awareness_keep_allowed`를 `component_scores`에 남김
4. `p_false_break`의 `forecast_reasons`에 BF1 reason trace를 같이 남김
5. transition metadata에 `bridge_first_v1` summary를 함께 노출

즉 이번 구현으로 transition forecast는

- 기존 scene/evidence/belief/barrier 기반 점수
- BF1 bridge 기반 wait/false-break 보정

을 같이 설명할 수 있게 됐다.

### 2-3. consumer check state에 BF1 awareness preserve 추가

아래 파일에 BF1 awareness wiring을 추가했다.

- [consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/consumer_check_state.py)

이번 패스에서 추가한 것은 아래와 같다.

1. payload 안의 `forecast_features_v1.metadata.bridge_first_v1.act_vs_wait_bias_v1`를 읽는 helper
2. soft wait 장면에서 `awareness_keep_allowed`가 참이고,
   `act_vs_wait_bias`는 충분하고,
   `false_break_risk`가 과하지 않으면
   완전히 꺼진 display를 `OBSERVE awareness`로 복원하는 최소 규칙
3. 아래 trace surface 추가
   - `bridge_first_adjustment_reason`
   - `bridge_act_vs_wait_bias`
   - `bridge_false_break_risk`
   - `bridge_awareness_keep_allowed`

즉 이제는

- `entry-ready`는 아니지만
- `완전 무표정하면 안 되는 장면`

을 BF1 bridge로 설명 가능하게 됐다.

## 3. 이번 패스에서 잠근 계약

이번 BF1 구현은 아래 원칙을 지킨다.

### 3-1. BF1은 owner가 아니다

BF1은 scene owner를 대체하지 않는다.

- scene가 자리 의미를 정한다
- BF1은 act/wait/awareness 강도를 조정한다

### 3-2. BF1은 raw 추가 트랙이 아니다

이번 구현은 raw field를 더 넣지 않았다.

- `State / Evidence / Belief / Barrier` 요약만 사용
- `secondary_harvest` direct-use 추가 없음
- `order_book` collector 수정 없음

즉 `bridge-first` 원칙을 그대로 유지했다.

### 3-3. BF1은 additive first pass다

이번 패스는 기존 forecast/consumer 구조를 뒤집지 않고, 아래처럼 약하게 연결했다.

- forecast: `false_break_pressure`에 가벼운 blend
- consumer: `awareness preserve`에만 제한적으로 사용

즉 대규모 self-tuning이 아니라 first-pass bridge다.

## 4. 테스트

이번 BF1에서 새로 잠근 테스트는 아래와 같다.

- [test_forecast_contract.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_forecast_contract.py)
  - feature metadata에 BF1 bridge summary가 노출되는지
  - transition forecast metadata / reason trace에 BF1이 같이 남는지

- [test_consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_consumer_check_state.py)
  - NAS breakout reclaim 장면에서
    soft-wait 때문에 완전히 꺼지던 display가
    BF1 bridge로 `OBSERVE awareness`로 복원되는지

실행 결과:

- targeted: `77 passed`
- full unit: `1179 passed, 127 warnings`

즉 BF1 first-pass wiring은 현재 unit 기준 회귀 없이 잠겼다.

## 5. 이번 구현의 해석

이번 BF1로 확인된 건 아래다.

1. `false-break / wait discrimination`을 bridge summary로 따로 뽑을 수 있다.
2. 이 bridge는 forecast 안쪽에서만 쓰는 게 아니라, chart/product acceptance의 awareness preserve에도 바로 연결할 수 있다.
3. 지금 필요한 것은 broad raw add가 아니라, 이렇게 `작은 bridge를 먼저 만들고 연결하는 것`이다.

즉 SF6 close-out의 결론이었던

- `raw_addition_priority = low`
- `bridge_addition_priority = high`

가 실제 코드로도 확인된 셈이다.

## 6. 아직 안 한 것

이번 BF1 first-pass에서는 아래는 아직 하지 않았다.

- `trade_management` 쪽 hold bridge
- `fast_cut_risk` bridge
- `secondary_harvest` direct-use 확장
- `activation projection` bridge
- symbol별 세부 threshold 미세조정

즉 BF1은 `transition + awareness`까지만 연 첫 패스다.

## 7. 다음 액션

가장 자연스러운 다음 순서는 아래 둘 중 하나다.

1. `BF1-F audit / close-out`
   - latest audit에서 BF1 영향 확인
   - false-break / wait discrimination이 실제로 개선되는지 재검토

2. `BF2 management_hold_reward_hint_v1`
   - management 쪽 가장 약한 gap을 다음 bridge로 연결

현재 흐름상으로는 `BF1 close-out을 짧게 정리한 뒤 BF2`로 가는 게 가장 자연스럽다.

## 8. 한 줄 요약

```text
BF1은 state/evidence/belief/barrier를 act_vs_wait_bias / false_break_risk / awareness_keep_allowed로 요약해,
transition forecast와 product acceptance wait awareness를 처음으로 같은 bridge로 연결한 first-pass 구현이다.
```
