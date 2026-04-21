# D12. NAS/BTC Symbol-Specific Pilot Surface Extension

## 목적

- XAU에만 있던 `pilot mapping -> read-only surface -> decomposition validation` 구조를 `NAS100`, `BTCUSD`에도 올린다.
- 단, XAU처럼 바로 검증 완료로 보지 않고, 각 심볼의 현재 calibration 상태를 반영한 `ACTIVE_PILOT / REVIEW_PENDING` 상태를 같이 surface한다.
- 목표는 XAU 예외를 복제하는 것이 아니라, 공용 decomposition 언어가 NAS/BTC에도 같은 방식으로 읽히는지 확인하는 것이다.

## 왜 필요한가

- D10은 `common slot vocabulary`가 NAS/BTC에도 붙는다는 걸 보여줬다.
- 하지만 아직 XAU처럼
  - pilot window catalog
  - symbol-specific read-only row surface
  - dominance / should-have-done 검증 묶음
  을 심볼별로 따로 볼 수는 없다.
- 사용자가 원하는 것도 바로 이 지점이다.
  - NAS와 BTC도 XAU처럼 “이 심볼 안에서 어떤 slot으로 읽히는지”를 직접 보고 싶다.

## 범위

### NAS

- `nas_pilot_mapping_contract_v1`
- `nas_readonly_surface_contract_v1`
- `nas_decomposition_validation_contract_v1`

### BTC

- `btc_pilot_mapping_contract_v1`
- `btc_readonly_surface_contract_v1`
- `btc_decomposition_validation_contract_v1`

## 설계 원칙

- 심볼별 surface는 `XAU 전용 로직 복붙`이 아니라 공용 decomposition 결과를 심볼별 prefix로 재표현하는 층이다.
- XAU처럼
  - pilot mapping은 retained evidence catalog
  - readonly surface는 runtime row visibility
  - validation은 dominance / should-have-done calibration join
  으로 역할을 분리한다.
- `dominant_side`는 계속 dominance layer만 바꿀 수 있다.
- NAS/BTC extension도 read-only다.

## NAS pilot 방향

- `NAS100_UP_CONTINUATION_BREAKOUT_HELD_V1`는 `ACTIVE_PILOT`
- `NAS100_DOWN_CONTINUATION_PENDING_V1`는 `REVIEW_PENDING`
- NAS는 현재 `breakout / continuation / stage readability`를 먼저 보는 심볼로 둔다.

## BTC pilot 방향

- `BTCUSD_UP_CONTINUATION_LOWER_RECOVERY_PENDING_V1`
- `BTCUSD_DOWN_CONTINUATION_UPPER_DRIFT_PENDING_V1`
  를 retained window catalog로 올린다.
- BTC는 현재 `recovery / drift / mixed caution`을 더 명시적으로 표면화한다.

## readonly surface 목적

- NAS row에서
  - `nas_polarity_slot_v1`
  - `nas_intent_slot_v1`
  - `nas_continuation_stage_v1`
  - `nas_state_slot_core_v1`
  를 바로 읽게 한다.
- BTC row에서도 같은 구조로
  - `btc_polarity_slot_v1`
  - `btc_intent_slot_v1`
  - `btc_continuation_stage_v1`
  - `btc_state_slot_core_v1`
  를 읽게 한다.

## validation 목적

- XAU처럼 NAS/BTC도
  - alignment
  - should-have-done candidate
  - over_veto / under_veto
  - error_type
  를 심볼별 표면으로 읽게 한다.
- 이건 실행 명령이 아니라 calibration teacher 축이다.

## 완료 기준

- `NAS100`, `BTCUSD`에 대해 pilot/read-only/validation 3단 summary와 artifact가 생성된다.
- runtime detail에서 NAS/BTC row 필드를 공통 계약으로 읽을 수 있다.
- XAU처럼 심볼별 decomposition surface를 비교할 수 있다.

## 상태 기준

- `READY`: NAS/BTC 모두 pilot/read-only/validation surface가 정상 생성됨
- `HOLD`: 한 심볼은 정상, 다른 심볼은 부분 surface
- `BLOCKED`: NAS/BTC extension이 runtime payload를 깨거나 summary를 누락함
