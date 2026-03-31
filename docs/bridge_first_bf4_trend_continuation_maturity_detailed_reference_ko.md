# BF4 Trend Continuation Maturity Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 목적

BF4는 `trade management forecast`가

- 지금 장면이 단순 continuation 흉내가 아니라 실제 trend continuation maturity를 갖는지
- 구조 tailwind가 있어 hold/reach confidence를 더 줄 수 있는지
- exhaustion 때문에 trend confidence를 과신하면 안 되는지

를 작은 bridge summary로 읽도록 만드는 단계다.

BF3가 `왜 빨리 끊어야 하는가`를 다뤘다면, BF4는 `왜 계속 들고 갈 수 있는가`를 trend 관점에서 다룬다.

## 2. 왜 BF4가 필요한가

SF4 / SF5 기준 management 쪽 gap은 아래처럼 약했다.

- `p_continue_favor separation_gap = 0.0475`
- `p_fail_now separation_gap = 0.0055`

즉 관리 단계에서

- continuation value가 진짜 있는 장면
- trend slice에서 reach/edge-to-edge를 더 봐도 되는 장면
- exhaustion 때문에 maturity를 낮춰야 하는 장면

의 차이를 더 잘 드러낼 bridge가 필요했다.

## 3. 입력 원칙

BF4도 새로운 raw를 추가하지 않는다.

입력은 기존 semantic/forecast 입력만 사용한다.

- `State`
- `Evidence`
- `Belief`
- `Barrier`

구체적으로는 아래 값을 주로 쓴다.

- `session_regime_state`
- `session_expansion_state`
- `topdown_slope_state`
- `topdown_confluence_state`
- `quality_state_label`
- `session_exhaustion_state`
- `execution_friction_state`
- `event_risk_state`
- dominant continuation evidence / total evidence
- dominant belief / persistence
- `belief_spread`
- `belief_instability`
- `position_conflict_score`
- `middle_neutrality`
- middle chop / conflict / side barriers

## 4. canonical summary shape

BF4의 canonical output은 아래 3개다.

- `continuation_maturity`
- `exhaustion_pressure`
- `trend_hold_confidence`

### 4-1. continuation_maturity

지금 장면이 continuation 구조로 얼마나 성숙해졌는지를 0~1로 요약한 값이다.

### 4-2. exhaustion_pressure

지금 장면이 trend continuation처럼 보여도 session exhaustion 때문에 hold/reach를 과신하면 안 되는 정도를 0~1로 요약한 값이다.

### 4-3. trend_hold_confidence

trend slice에서 `continue / reach` 쪽으로 soft confidence를 더 줄 수 있는가를 0~1로 요약한 값이다.

## 5. owner 원칙

BF4도 owner가 아니다.

- scene / management base math가 원래 owner
- BF4는 `trend continuation confidence`를 soft raise 하는 modifier

즉 BF4는

- 장면을 새로 만들지 않고
- 기존 management math를 뒤집지 않고
- additive first-pass로만 연결한다.

## 6. 연결 위치

### 6-1. feature metadata

- [forecast_features.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/forecast_features.py)

여기에 `bridge_first_v1.trend_continuation_maturity_v1`를 만든다.

### 6-2. trade management forecast

- [forecast_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/forecast_engine.py)

여기서 BF4 bridge를 읽어 아래에 soft blend 한다.

- `p_continue_favor`
- `p_fail_now`
- `p_recover_after_pullback`
- `p_reach_tp1`
- `p_opposite_edge_reach`

### 6-3. future product acceptance

BF4는 이번 패스에서 chart/product acceptance까지 직접 연결하진 않는다.
대신 이후 hold/exit acceptance 재조정에서 공통 bridge로 재사용할 수 있게 metadata를 남긴다.

## 7. 이번 패스의 기대 효과

- `p_continue_favor`가 trend maturity 장면에서 조금 더 벌어진다.
- `p_reach_tp1`, `p_opposite_edge_reach`가 trend tailwind를 더 반영한다.
- `p_fail_now`가 mature trend 장면에서 조금 더 눌린다.
- management forecast가 왜 trend hold confidence 쪽으로 기울었는지 reason trace가 richer 해진다.

## 8. 이번 패스에서 하지 않을 것

- raw collector 재작업 안 함
- advanced input reliability bridge까지 같이 넣지 않음
- product acceptance hold/exit까지 바로 동시 연결 안 함

즉 BF4는 `trend continuation maturity`만 먼저 여는 단계다.

## 9. 완료 기준

1. feature metadata에 BF4 summary가 남는다.
2. trade management forecast metadata에 BF4 trace가 남는다.
3. management 테스트에서 BF4가 continue/reach 쪽을 실제로 조금 밀어준다.
4. 회귀 없이 전체 unit이 통과한다.

## 10. 한 줄 요약

```text
BF4는 trend continuation 장면을 continuation_maturity / exhaustion_pressure / trend_hold_confidence로 요약해, trade management forecast의 continue/reach 쪽 설명력을 높이는 positive trend bridge다.
```
