# State / Forecast Validation Detailed Reference

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 현재 제품 acceptance 조정 과정에서 제기된 아래 질문을
구체적인 검증 과제로 바꾸기 위한 기준 문서다.

- `state에 읽히는 데이터가 부족한가`
- `forecast가 state/evidence/belief/barrier를 제대로 먹고 있는가`
- `예측 정확도를 높이려면 raw를 더 넣어야 하는가`
- `아니면 이미 있는 입력의 활성화/커버리지/정보가치를 먼저 검증해야 하는가`

이 문서의 결론은 단순하다.

```text
지금 단계에서 제일 먼저 해야 할 일은
state raw를 무작정 더 넣는 것이 아니라,
이미 들어오는 state / advanced input / semantic harvest가
얼마나 살아 있고 실제로 forecast와 product acceptance에 기여하는지
검증하는 것이다.
```

## 2. 왜 지금 이 검증이 필요한가

현재 chart/check acceptance 조정은
scene 기반으로 먼저 맞추고,
그 위에 state-aware modifier를 얹는 방향으로 가고 있다.

이 방향은 맞지만, 계속 조정하다 보면 아래 문제가 생길 수 있다.

1. state raw는 많이 들어오는데 실제론 거의 default/zero만 쓰이고 있을 수 있다.
2. forecast feature bundle은 풍부한데 실제 branch score에는 일부만 쓰일 수 있다.
3. XAU/NAS/BTC의 체감 불만이 raw 부족 때문인지, activation 부족 때문인지 구분이 안 될 수 있다.
4. 검증 없이 입력만 늘리면 설명 불가능한 복잡도만 증가할 수 있다.

즉 지금 필요한 것은 `확장`보다 먼저 `가시화와 검증`이다.

## 3. 현재 구조에서 state/forecast가 연결되는 방식

현재 연결 흐름은 아래처럼 읽는 것이 정확하다.

```text
context_classifier
-> state builder / advanced input activation
-> state_vector_v2 / metadata
-> evidence / belief / barrier
-> forecast_features_v1
-> transition_forecast / trade_management_forecast
-> entry / wait / exit / display modifier 후보
```

### 3-1. state가 만들어지는 위치

- [builder.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\state\builder.py)
- [advanced_inputs.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\state\advanced_inputs.py)
- [context_classifier.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\context_classifier.py)

### 3-2. forecast feature bundle이 만들어지는 위치

- [forecast_features.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\core\forecast_features.py)
- [forecast_engine.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\core\forecast_engine.py)

### 3-3. 실행 계층이 읽는 위치

- [entry_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
- [entry_wait_context_contract.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_wait_context_contract.py)
- [entry_wait_state_bias_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_wait_state_bias_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)

## 4. 현재 이미 들어오고 있는 state 계열 입력

현재 raw/state 계열은 이미 생각보다 많이 들어오고 있다.

### 4-1. 기본 state raw

현재 `StateRawSnapshot` / `StateVectorV2`에 실리는 대표 값:

- market_mode
- direction_policy
- liquidity_state
- noise / conflict / alignment / disparity / volatility
- current RSI / ADX / +DI / -DI
- recent range mean / body mean
- SR level rank / SR touch count
- session box height ratio / session expansion progress / session position bias
- topdown spacing / slope / confluence
- spread / tick volume / real volume

기준 코드:

- [builder.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\state\builder.py)

### 4-2. advanced input

현재 advanced input 수집기는 아래를 다룬다.

- tick history
- order book
- event risk / shock event
- spread stress
- low participation
- wait conflict
- wait noise

기준 코드:

- [advanced_inputs.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\state\advanced_inputs.py)

### 4-3. execution bridge

이미 state는 execution-friendly bridge로도 요약돼 있다.

- wait_patience_gain
- confirm_aggression_gain
- hold_patience_gain
- fast_exit_risk_penalty
- patience_state_label
- topdown_state_label
- quality_state_label
- execution_friction_state
- session_exhaustion_state
- event_risk_state

기준 코드:

- [context_classifier.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\context_classifier.py)

## 5. 현재 forecast가 이미 harvest하는 입력

현재 forecast feature bundle은 semantic-only contract를 유지하면서도
꽤 많은 harvest를 하고 있다.

### 5-1. state_harvest

- session_regime_state
- session_expansion_state
- session_exhaustion_state
- topdown_spacing_state
- topdown_slope_state
- topdown_confluence_state
- spread_stress_state
- volume_participation_state
- execution_friction_state
- event_risk_state

### 5-2. belief_harvest

- dominant_side
- dominant_mode
- buy_streak
- sell_streak
- flip_readiness
- belief_instability

### 5-3. barrier_harvest

- edge_turn_relief_v1
- breakout_fade_barrier_v1
- middle_chop_barrier_v2
- session_open_shock_barrier_v1
- duplicate_edge_barrier_v1
- micro_trap_barrier_v1
- post_event_cooldown_barrier_v1

### 5-4. secondary_harvest

- advanced_input_activation_state
- tick_flow_state
- order_book_state
- source_current_rsi
- source_current_adx
- source_current_plus_di
- source_current_minus_di
- source_recent_range_mean
- source_recent_body_mean
- source_sr_level_rank
- source_sr_touch_count

기준 코드:

- [forecast_features.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\core\forecast_features.py)

## 6. 현재 부족하다고 볼 수 있는 지점

현재 부족한 것은 `raw 종류 자체`보다 아래 세 가지에 더 가깝다.

### 6-1. coverage / activation 검증 부족

우리가 아직 충분히 모르는 것:

- tick history가 실제로 심볼별로 얼마나 자주 active인가
- order book이 비어 있는 시간이 얼마나 많은가
- event risk가 default 0으로만 들어가는 구간이 얼마나 많은가
- advanced_input_activation_state가 실제로 active가 되는 비율은 어느 정도인가

즉 `있다`와 `실제로 살아 있다`는 다른 문제다.

### 6-2. 정보가치 검증 부족

forecast는 현재 많은 harvest를 metadata로 담고 있고,
usage trace도 남긴다.

하지만 아직 부족한 질문은 아래다.

- 어떤 state_harvest가 실제 branch score를 많이 바꾸는가
- belief/barrier harvest가 어떤 scene에서만 유효한가
- 심볼별로 유효한 harvest와 의미 없는 harvest가 다른가

즉 `연결은 돼 있다`와 `정확도에 실제로 기여한다`는 다른 문제다.

### 6-3. bridge summary 부족

raw 자체는 많지만 display/entry/wait/exit가 읽기 좋은
압축형 bridge는 아직 약하다.

예:

- chop_pressure
- directional_pressure
- exhaustion_pressure
- awareness_keep_allowed
- act_vs_wait_bias
- fast_cut_risk
- hold_reward_hint

이런 압축형 bridge가 있어야
raw를 직접 재해석하지 않고도
product acceptance와 forecast refinement를 더 쉽게 연결할 수 있다.

## 7. 지금 당장 raw를 더 넣어야 하는가

현재 판단은 아래와 같다.

### 7-1. 지금 당장 우선순위는 아님

무작정 raw를 더 넣는 것은 우선순위가 아니다.

이유:

1. 이미 state/advanced input raw는 많다.
2. forecast semantic harvest도 이미 풍부하다.
3. coverage / usage / value 검증 없이 raw만 늘리면 설명 불가능한 복잡도만 증가한다.

### 7-2. 다만 향후 추가 후보는 있음

검증 후 정말 부족하다고 판명되면
다음 같은 추가/요약 후보를 검토할 수 있다.

- continuation maturity score
- exhaustion pressure summary
- evidence freshness summary
- barrier collision imminence score
- advanced input reliability score

즉 다음 확장은 `raw 추가`보다 `가치가 검증된 bridge 추가` 쪽이 맞다.

## 8. 지금 필요한 검증 질문

이번 validation subtrack은 아래 질문에 답해야 한다.

1. state raw와 advanced input은 실제로 얼마나 자주 활성화되는가
2. 심볼별/시간대별/장세별로 어떤 값이 자주 default로 남는가
3. forecast branch는 harvest한 값 중 실제로 무엇을 많이 쓰는가
4. state/belief/barrier harvest는 어떤 slice에서만 유효한가
5. preview/shadow 기준으로 어떤 harvest가 성능에 기여하는가
6. chart acceptance / entry acceptance 조정에 재활용 가능한 bridge는 무엇인가

## 9. 이 subtrack의 범위

이번 subtrack은 아래를 다룬다.

- state coverage validation
- advanced input activation audit
- forecast harvest usage/value audit
- slice별 정보가치 점검
- 향후 bridge 후보 정리

이번 subtrack은 아래를 다루지 않는다.

- semantic ownership 변경
- raw detector 직접 사용
- forecast를 action owner로 승격
- product acceptance chart tuning 자체를 여기서 직접 조정하는 일

## 10. 완료 기준

이 subtrack이 닫혔다고 말하려면 아래가 필요하다.

1. state/advanced input coverage report가 있다
2. forecast harvest usage/value report가 있다
3. symbol/regime별 gap matrix가 있다
4. `지금 raw가 부족한지`, `활성화가 부족한지`, `bridge가 부족한지`를 구분해서 말할 수 있다
5. 다음 액션이 `추가 raw`, `bridge 요약`, `threshold 조정`, `무변경 유지` 중 무엇인지 결정된다

## 11. 한 줄 결론

```text
지금 필요한 것은 state raw를 무작정 더 넣는 일이 아니라,
이미 들어오는 state / advanced input / semantic harvest의 coverage와 정보가치를 검증하고,
그 결과를 바탕으로 forecast와 product acceptance에 필요한 bridge를 정리하는 것이다.
```
