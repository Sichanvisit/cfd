# BF2 Management Hold Reward Hint Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 목적

BF2는 `trade management forecast`가

- 지금 hold를 유지할 가치가 있는지
- edge-to-edge completion 쪽 tailwind가 있는지
- 바로 cut하는 것보다 patience를 주는 편이 나은지

를 작은 bridge summary로 읽도록 만드는 단계다.

BF1이 `WAIT vs act`를 다뤘다면, BF2는 `hold vs too-early cut`의 양수 방향 힌트를 다룬다.

## 2. 왜 BF2가 필요한가

SF4 / SF5 기준 management 쪽 gap은 아래처럼 약했다.

- `p_continue_favor separation_gap = 0.0475`
- `p_fail_now separation_gap = 0.0055`

즉 관리 단계에서

- 버텨도 되는 장면
- 아직 더 갈 가능성이 있는 장면
- 너무 빨리 잘라서 손해 보는 장면

의 차이를 더 잘 드러낼 bridge가 필요했다.

## 3. 입력 원칙

BF2는 새로운 raw를 추가하지 않는다.

입력은 기존 semantic/forecast 입력만 사용한다.

- `State`
- `Evidence`
- `Belief`
- `Barrier`

구체적으로는 아래 값을 주로 쓴다.

- `hold_patience_gain`
- `quality_state_label`
- `topdown_confluence_state`
- `execution_friction_state`
- `event_risk_state`
- `session_exhaustion_state`
- dominant total/path evidence
- dominant belief / persistence
- middle chop / conflict / side barriers

## 4. canonical summary shape

BF2의 canonical output은 아래 3개다.

- `hold_reward_hint`
- `edge_to_edge_tailwind`
- `hold_patience_allowed`

### 4-1. hold_reward_hint

지금 장면에서 hold를 더 유지할수록 reward가 날 가능성을 0~1로 요약한 값이다.

### 4-2. edge_to_edge_tailwind

지금 장면이 단순 소음 버티기 수준이 아니라,
실제로 목표 구간을 더 밀어붙일 tailwind가 있는지를 0~1로 요약한 값이다.

### 4-3. hold_patience_allowed

강한 hold reward까지는 아니더라도,
`너무 빨리 cut하지 말고 hold bias를 허용해도 되는가`
를 bool로 요약한 값이다.

## 5. owner 원칙

BF2도 owner가 아니다.

- scene / management base math가 원래 owner
- BF2는 `hold reward`를 soft boost 하는 modifier

즉 BF2는

- 장면을 새로 만들지 않고
- 기존 management math를 뒤집지 않고
- additive first-pass로만 연결한다.

## 6. 연결 위치

### 6-1. feature metadata

- [forecast_features.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/forecast_features.py)

여기에 `bridge_first_v1.management_hold_reward_hint_v1`를 만든다.

### 6-2. trade management forecast

- [forecast_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/forecast_engine.py)

여기서 BF2 bridge를 읽어 아래에 soft blend 한다.

- `p_continue_favor`
- `p_fail_now`
- `p_recover_after_pullback`
- `p_reach_tp1`
- `p_opposite_edge_reach`

### 6-3. future hold/exit acceptance

BF2는 이번 패스에서 chart/product acceptance까지 직접 연결하진 않는다.
대신 다음 hold/exit acceptance 재조정에서 공통 bridge로 재사용할 수 있게 metadata를 남긴다.

## 7. 이번 패스의 기대 효과

- `p_continue_favor`가 hold reward가 있는 장면에서 조금 더 벌어진다.
- `p_reach_tp1`, `p_opposite_edge_reach`가 edge-to-edge tailwind를 더 반영한다.
- management forecast가 왜 hold 쪽으로 기울었는지 reason trace가 richer 해진다.

## 8. 이번 패스에서 하지 않을 것

- fast cut risk bridge까지 같이 넣지 않음
- raw collector 재작업 안 함
- product acceptance hold/exit까지 바로 동시 연결 안 함

즉 BF2는 `positive hold hint`만 먼저 여는 단계다.

## 9. 완료 기준

1. feature metadata에 BF2 summary가 남는다.
2. trade management forecast metadata에 BF2 trace가 남는다.
3. management 테스트에서 BF2가 continue / reach 쪽을 실제로 조금 밀어준다.
4. 회귀 없이 전체 unit이 통과한다.

## 10. 한 줄 요약

```text
BF2는 hold를 더 줄 가치가 있는 장면을 hold_reward_hint / edge_to_edge_tailwind / hold_patience_allowed로 요약해, trade management forecast에 처음 연결하는 positive hold bridge다.
```
