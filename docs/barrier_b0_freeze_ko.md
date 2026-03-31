# Barrier B0 Freeze

## 고정 문장

`Barrier는 진입을 찾는 레이어가 아니라, 지금은 막아야 하는지를 판단하는 차단 레이어다.`

## 이번 Freeze에서 고정한 것

- `Barrier`는 `BUY/SELL` 방향을 새로 만들지 않는다.
- `Barrier`는 `Position`의 위치 owner를 침범하지 않는다.
- `Barrier`는 `Response`의 사건 owner를 침범하지 않는다.
- `Barrier`는 `State`의 시장 성격 owner를 침범하지 않는다.
- `Barrier`는 `Evidence`의 근거 owner를 침범하지 않는다.
- `Barrier`는 `Belief`의 지속성 owner를 침범하지 않는다.

## 허용되는 역할

- `entry_blocking`
- `execution_risk_blocking`
- `scene_relief_scaling`

## 금지되는 역할

- `position_location_identity`
- `response_event_identity`
- `state_regime_identity`
- `evidence_strength_identity`
- `belief_persistence_identity`
- `direct_buy_sell_side_identity`
- `direct_action_identity`

## 완료 기준

- `barrier_state_v1.metadata.semantic_owner_contract = barrier_blocking_only_v1`
- `barrier_state_v1.metadata.barrier_freeze_phase = BR0`
- `owner_boundaries_v1`로 owner 침범 금지 명시
- `Barrier`가 side creator처럼 행동하지 않음을 테스트로 고정
