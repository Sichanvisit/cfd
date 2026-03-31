# BF3 Management Fast Cut Risk Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 목적

BF3는 `trade management forecast`가

- 지금은 hold보다 빠른 cut을 더 진지하게 봐야 하는지
- 구조 충돌이나 장벽 collision risk가 큰지
- event / friction / exhaustion 때문에 hold를 과신하면 안 되는지

를 작은 bridge summary로 읽도록 만드는 단계다.

BF2가 `hold를 더 줄 가치`를 다뤘다면, BF3는 `왜 빨리 끊는 쪽을 더 주의해야 하는가`를 다룬다.

## 2. 왜 BF3가 필요한가

SF4 / SF5 기준 management 쪽 gap은 아래처럼 약했다.

- `p_continue_favor separation_gap = 0.0475`
- `p_fail_now separation_gap = 0.0055`

즉 관리 단계에서

- 계속 버텨도 되는 장면
- 지금은 빨리 끊고 재진입을 더 보는 편이 나은 장면
- event/friction/collision 때문에 hold confidence를 낮춰야 하는 장면

의 차이를 더 잘 드러낼 bridge가 필요했다.

## 3. 입력 원칙

BF3도 새로운 raw를 추가하지 않는다.

입력은 기존 semantic/forecast 입력만 사용한다.

- `State`
- `Evidence`
- `Belief`
- `Barrier`

구체적으로는 아래 값을 주로 쓴다.

- `fast_exit_risk_penalty`
- `countertrend_penalty`
- `liquidity_penalty`
- `volatility_penalty`
- `execution_friction_state`
- `event_risk_state`
- `session_exhaustion_state`
- dominant total evidence / belief / persistence
- `flip_readiness`
- `belief_instability`
- `position_conflict_score`
- `middle_neutrality`
- middle chop / conflict / side barriers

## 4. canonical summary shape

BF3의 canonical output은 아래 4개다.

- `fast_cut_risk`
- `collision_risk`
- `event_caution`
- `cut_now_allowed`

### 4-1. fast_cut_risk

지금 장면에서 `hold보다 빠른 cut` 쪽으로 기우는 압력을 0~1로 요약한 값이다.

### 4-2. collision_risk

middle chop / conflict / side barrier / structural collision 때문에
hold를 강하게 밀면 안 되는 정도를 0~1로 요약한 값이다.

### 4-3. event_caution

event risk가 cut-now 쪽 caution을 얼마나 올리는지 0~1로 요약한 값이다.

### 4-4. cut_now_allowed

강한 hold modifier를 그대로 두기보다,
`지금은 fail_now / better_reentry_if_cut`을 조금 더 밀어도 되는가`
를 bool로 요약한 값이다.

## 5. owner 원칙

BF3도 owner가 아니다.

- scene / management base math가 원래 owner
- BF3는 `fast cut caution`을 soft raise 하는 modifier

즉 BF3는

- 장면을 새로 만들지 않고
- 기존 management math를 뒤집지 않고
- additive first-pass로만 연결한다.

## 6. 연결 위치

### 6-1. feature metadata

- [forecast_features.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/forecast_features.py)

여기에 `bridge_first_v1.management_fast_cut_risk_v1`를 만든다.

### 6-2. trade management forecast

- [forecast_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/forecast_engine.py)

여기서 BF3 bridge를 읽어 아래에 soft blend 한다.

- `p_continue_favor`
- `p_fail_now`
- `p_recover_after_pullback`
- `p_reach_tp1`
- `p_opposite_edge_reach`
- `p_better_reentry_if_cut`

### 6-3. future exit caution / product acceptance

BF3는 이번 패스에서 chart/product acceptance까지 직접 연결하진 않는다.
대신 이후 exit acceptance 재조정에서 공통 bridge로 재사용할 수 있게 metadata를 남긴다.

## 7. 이번 패스의 기대 효과

- `p_fail_now`가 fast cut caution 장면에서 조금 더 벌어진다.
- `p_better_reentry_if_cut`가 event/collision pressure를 더 반영한다.
- `p_continue_favor`, `p_reach_tp1`, `p_opposite_edge_reach`가 위험 장면에서 과신되지 않는다.
- management forecast가 왜 cut 쪽으로 기울었는지 reason trace가 richer 해진다.

## 8. 이번 패스에서 하지 않을 것

- raw collector 재작업 안 함
- order_book targeted collector fix 안 함
- product acceptance exit wiring까지 동시 연결 안 함
- secondary activation reliability bridge는 아직 안 넣음

즉 BF3는 `negative fast-cut caution`만 먼저 여는 단계다.

## 9. 완료 기준

1. feature metadata에 BF3 summary가 남는다.
2. trade management forecast metadata에 BF3 trace가 남는다.
3. management 테스트에서 BF3가 fail/reentry 쪽을 실제로 조금 밀어준다.
4. 회귀 없이 전체 unit이 통과한다.

## 10. 한 줄 요약

```text
BF3는 event/friction/collision 때문에 hold를 과신하면 안 되는 장면을 fast_cut_risk / collision_risk / event_caution / cut_now_allowed로 요약해, trade management forecast의 fail/reentry 쪽 설명력을 높이는 negative cut-caution bridge다.
```
