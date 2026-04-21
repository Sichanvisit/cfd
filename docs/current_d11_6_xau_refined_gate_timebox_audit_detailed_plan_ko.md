# D11-6. XAU Refined Gate Timebox Audit 상세 계획

## 목적

- 현재 `XAUUSD` row가 refined bounded lifecycle gate를 통과하지 못하는 이유를 `persisted runtime row`와 `effective recomputation row`를 나란히 비교하며 읽는다.
- `실제 gate failure`와 `runtime_status.detail.json 미갱신`을 분리한다.
- `pilot match`, `ambiguity`, `texture`, `entry/hold policy`, `alignment` 중 무엇이 1차 driver인지 row/artifact로 고정한다.

## 왜 필요한가

현재 XAU는 구조상으로는 다음이 동시에 보일 수 있다.

- `xau_state_slot_core_v1 = BULL_RECOVERY_ACCEPTANCE`
- `entry_policy_v1 = DELAYED_ENTRY`
- `hold_policy_v1 = STRONG_HOLD`
- `reduce_policy_v1 = REDUCE_FAVOR`

그런데 persisted row에는 아래가 비어 있을 수 있다.

- `lifecycle_policy_alignment_state_v1`
- `lifecycle_canary_candidate_state_v1`
- `xau_lifecycle_canary_risk_gate_v1`

이 경우 우리는 두 가지를 분리해야 한다.

1. 현재 live row가 정말 gate를 못 통과하는가
2. 아니면 최신 코드 체인이 아직 persisted payload에 반영되지 않은 것뿐인가

이 분리를 하지 않으면 XAU canary를 잘못 해석하게 된다.

## 진단 원칙

- persisted row를 truth처럼 취급하지 않는다
- current row를 지금 코드 체인으로 다시 흘려 `effective row`를 만든다
- gate failure는 아래 순서로 읽는다
  1. alignment
  2. pilot match
  3. ambiguity
  4. texture
  5. entry policy
  6. hold policy
  7. residual canary scope
- `missing persisted fields`는 gate failure와 별도 축으로 surface한다

## 입력

- `latest_signal_by_symbol["XAUUSD"]`
- upstream 재계산 체인
  - `xau_readonly_surface`
  - `state_slot_execution_interface_bridge`
  - `state_slot_position_lifecycle_policy`
  - `execution_policy_shadow_audit`
  - `bounded_lifecycle_canary`

## 출력

### row-level

- `xau_refined_gate_timebox_audit_profile_v1`
- `xau_gate_timebox_audit_state_v1`
- `xau_gate_failure_stage_v1`
- `xau_gate_failure_primary_driver_v1`
- `xau_gate_saved_vs_effective_state_v1`
- `xau_gate_persisted_alignment_state_v1`
- `xau_gate_effective_alignment_state_v1`
- `xau_gate_persisted_candidate_state_v1`
- `xau_gate_effective_candidate_state_v1`
- `xau_gate_persisted_risk_gate_v1`
- `xau_gate_effective_risk_gate_v1`
- `xau_gate_effective_scope_detail_v1`
- `xau_gate_persisted_field_gap_v1`
- `xau_gate_timebox_reason_summary_v1`

### payload-level

- `xau_refined_gate_timebox_audit_contract_v1`
- `xau_refined_gate_timebox_audit_summary_v1`
- `xau_refined_gate_timebox_audit_artifact_paths`

## 상태 기준

- `READY`
  - XAU row가 있고 persisted/effective 비교가 가능함
- `HOLD`
  - XAU row는 있지만 effective recomputation이 core slot을 못 만듦
- `NOT_APPLICABLE`
  - XAU row가 없음

## saved vs effective 해석

- `CONSISTENT`
  - persisted 필드와 effective 필드가 같음
- `PERSISTED_FIELDS_MISSING`
  - persisted row에 gate 판단 핵심 필드가 없음
- `PERSISTED_OUTDATED`
  - persisted 값은 있으나 effective 값과 다름

## failure stage 해석

- `ALIGNMENT`
  - lifecycle shadow audit alignment가 아직 `ALIGNED`가 아님
- `PILOT_MATCH`
  - XAU current row가 active/partial pilot match를 못 충족함
- `AMBIGUITY`
  - ambiguity가 높아 refined gate에서 보류됨
- `TEXTURE`
  - drift texture 때문에 보류됨
- `ENTRY_POLICY`
  - entry posture가 너무 열려 있음
- `HOLD_POLICY`
  - hold posture가 gate 요구치보다 약함
- `CANARY_SCOPE`
  - 위 조건은 통과했지만 아직 bounded-ready slice까지는 못 감

## 금지선

- 이 audit은 execution/state25를 바꾸지 않는다
- 이 audit은 XAU row를 강제로 `BOUNDED_READY`로 바꾸지 않는다
- persisted row가 비어 있어도 그 자체를 “시장 해석 실패”로 오인하지 않는다
