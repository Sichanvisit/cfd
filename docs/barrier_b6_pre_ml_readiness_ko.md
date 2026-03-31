# Barrier B6 Pre-ML Readiness

## 목표

나중에 ML calibration이 붙어도 `Barrier`가 semantic owner를 빼앗기지 않고, 안전한 feature 공급자로만 쓰이게 고정한다.

고정 문장:

`Barrier는 막아야 하는지를 판단하는 차단 레이어이며, ML은 Barrier를 feature로 소비할 수는 있어도 Barrier의 owner 역할을 대체할 수 없다.`

---

## 필수 출력

아래 값은 이미 `BarrierState` 1급 출력으로 존재한다.

- `buy_barrier`
- `sell_barrier`
- `conflict_barrier`
- `middle_chop_barrier`
- `direction_policy_barrier`
- `liquidity_barrier`

이 값들은 ML 없이도 의미 설명이 가능해야 한다.

---

## 추천 출력

아래 값은 `barrier_state_v1.metadata`에서 직접 확인 가능하다.

- `edge_turn_relief_score`
- `breakout_fade_barrier_score`
- `execution_friction_barrier_score`
- `event_risk_barrier_score`

의미:

- `edge_turn_relief_score`
  - edge turn 장면에서 barrier를 얼마나 풀어줬는지
- `breakout_fade_barrier_score`
  - breakout continuation 장면에서 역추세 fade를 얼마나 더 막는지
- `execution_friction_barrier_score`
  - execution 환경이 나쁠수록 barrier를 얼마나 올려야 하는지
- `event_risk_barrier_score`
  - event/news risk가 barrier를 얼마나 올리는지

---

## 계약

런타임 메타데이터:

- `barrier_pre_ml_phase = BR6`
- `pre_ml_readiness_contract_v1.phase = BR6`
- `pre_ml_readiness_contract_v1.status = READY`
- `pre_ml_readiness_contract_v1.ml_usage_role = feature_only_not_owner`
- `pre_ml_readiness_contract_v1.owner_collision_allowed = false`

즉 ML은:

- `Barrier`를 calibration feature로는 사용 가능
- 하지만 아래를 새로 정의하면 안 된다
  - position identity
  - response event identity
  - state regime identity
  - evidence strength identity
  - belief persistence identity
  - direct action ownership

---

## 안전한 ML 사용 대상

- `entry_block_threshold_calibration`
- `scene_relief_calibration`
- `execution_friction_calibration`
- `event_risk_block_calibration`

즉 ML은 barrier의 숫자를 조금 보정할 수는 있어도, `Barrier`가 하는 "막을지 말지"의 semantic 질문 자체를 새 owner로 가져가면 안 된다.

---

## 완료 기준

- ML 없이도 barrier 설명 가능
- ML이 붙어도 owner 충돌 없음
- 필수 core barrier는 그대로 유지
- 추천 score는 metadata에서 직접 조회 가능
