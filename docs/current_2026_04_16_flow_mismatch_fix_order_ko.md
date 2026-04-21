# Flow Mismatch Fix Order

## 1단계: NAS

- 목표:
  - `BUY_WATCH + dominance BULL`인데 `FLOW_OPPOSED`로 눌리는 케이스를 먼저 줄인다.
- 수정 위치:
  - `backend/services/state_slot_symbol_extension_surface.py`
- 기준:
  - pending review bearish family만으로 bearish slot 확정 금지
  - bullish continuation evidence가 강하면 `BULL_CONTINUATION_*` 재분류 허용

## 2단계: XAU

- 목표:
  - `BULL slot + BULL dominance`인데 `AMBIGUITY_HIGH` 하나로 계속 `UNCONFIRMED`에 머무는 케이스를 줄인다.
- 수정 위치:
  - `backend/services/flow_structure_gate_contract.py`
  - 필요 시 `backend/services/aggregate_directional_flow_metrics_contract.py`
- 기준:
  - ambiguity가 높아도 polarity alignment가 깨지지 않으면 hard opposed 대신 bounded hold/unconfirmed로 남길지 검토

## 3단계: BTC

- 목표:
  - `dominance = NONE` 경계 상태를 곧장 `FLOW_OPPOSED`로 읽는 과긴축을 줄인다.
- 수정 위치:
  - `backend/services/flow_structure_gate_contract.py`
  - dominance surface 연계부
- 기준:
  - `NONE`은 true opposite가 아니라 unresolved/boundary일 수 있으므로 분기 완화 필요

## 운영 원칙

- 순서는 `NAS -> XAU -> BTC`
- 공통 rule을 먼저 흔들지 않는다
- 각 단계마다 runtime row / artifact / test를 다시 확인한다
- 해석 문제를 threshold tuning으로 덮지 않는다
