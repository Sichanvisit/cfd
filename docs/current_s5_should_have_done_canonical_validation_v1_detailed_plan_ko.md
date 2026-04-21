# S5. Should-Have-Done / Canonical Surface 결합 검증 상세 계획

## 1. 목적

S5의 목적은 S4 `dominance shadow`가 실제 review 가치가 있는지
`should-have-done` 후보와 `canonical surface` 관점에서 검증 가능한 row-level surface를 만드는 것이다.

즉 이 단계는

- dominance가 continuation을 과소승격했는지
- friction을 reversal로 과대해석했는지
- boundary에 너무 오래 머물렀는지
- 진짜 reversal을 놓쳤는지

를 공통 오류 언어로 보이게 만드는 단계다.

## 2. 왜 S5가 필요한가

S4까지 오면 dominance는 surface된다.
하지만 아직 남는 질문은 있다.

- 이 dominance 해석이 실제로 review 가치가 있는가
- 기존 should-have-done 후보와 얼마나 정렬되는가
- canonical runtime/execution divergence를 더 잘 설명하는가

S5는 이 질문에 답하기 위한 검증층이다.

## 3. 핵심 산출물

### 3-1. Row-level validation surface

- `dominance_validation_profile_v1`
- `dominance_expected_side_v1`
- `dominance_expected_mode_v1`
- `dominance_expected_caution_level_v1`
- `dominance_vs_canonical_alignment_v1`
- `dominance_should_have_done_candidate_v1`
- `dominance_error_type_v1`
- `overweighted_caution_fields_v1`
- `undervalued_continuation_evidence_v1`
- `dominance_validation_reason_summary_v1`

### 3-2. Detail payload surface

- `dominance_validation_contract_v1`
- `dominance_validation_summary_v1`
- `dominance_validation_artifact_paths`

## 4. expected dominance 해석 원칙

### 4-1. expected side

기본 expected side는 canonical direction을 따른다.

- `canonical_direction_annotation_v1 = UP` -> `BULL`
- `canonical_direction_annotation_v1 = DOWN` -> `BEAR`
- `canonical_direction_annotation_v1 = NEUTRAL` -> `NONE`

### 4-2. expected mode

기본 expected mode는 canonical phase와 consumer veto tier를 함께 본다.

- `canonical_phase_v1 = REVERSAL` 또는 `consumer_veto_tier_v1 = REVERSAL_OVERRIDE`
  -> `REVERSAL_RISK`
- `consumer_veto_tier_v1 = FRICTION_ONLY` and expected side exists
  -> `CONTINUATION_WITH_FRICTION`
- `canonical_phase_v1 = CONTINUATION` and expected side exists
  -> `CONTINUATION`
- 나머지
  -> `BOUNDARY`

### 4-3. expected caution level

- `REVERSAL_OVERRIDE` 또는 canonical divergence가 심하면 `HIGH`
- `FRICTION_ONLY`는 기본 `MEDIUM`
- plain continuation은 `LOW`
- boundary는 `MEDIUM~HIGH`

## 5. dominance_error_type_v1

v1 error type enum:

- `ALIGNED`
- `CONTINUATION_UNDERPROMOTED`
- `REVERSAL_OVERCALLED`
- `BOUNDARY_STAYED_TOO_LONG`
- `FRICTION_MISREAD_AS_REVERSAL`
- `TRUE_REVERSAL_MISSED`

### 판정 예

- expected continuation인데 dominance가 `BOUNDARY`
  -> `CONTINUATION_UNDERPROMOTED`
- expected friction continuation인데 dominance가 `REVERSAL_RISK`
  -> `FRICTION_MISREAD_AS_REVERSAL`
- expected continuation인데 dominance가 `REVERSAL_RISK`
  -> `REVERSAL_OVERCALLED`
- expected reversal인데 dominance가 reversal로 못 감
  -> `TRUE_REVERSAL_MISSED`
- canonical divergence가 있는데 boundary에 오래 머무는 경우
  -> `BOUNDARY_STAYED_TOO_LONG`

## 6. caution / continuation evidence 설명 필드

### overweighted_caution_fields_v1

현재 row에서 과대작동했을 가능성이 있는 caution 계층을 기록한다.

예:

- `upper_reject_confirm`
- `outer_band_reversal_support_required_observe`
- `blocked_by=energy_soft_block`
- `forecast_wait_bias`
- `belief_reduce_alert`
- `barrier_wait_bias`

### undervalued_continuation_evidence_v1

현재 row에서 과소평가됐을 가능성이 있는 continuation 증거를 기록한다.

예:

- `breakout_held`
- `previous_box_above`
- `with_htf`
- `overlay_enabled`
- `breakout_candidate_direction`
- `local_structure_continuation_favor`
- `breakout_hold_quality`
- `body_drive_support`

## 7. summary artifact

최소 포함:

- `symbol_count`
- `candidate_count`
- `dominance_error_type_count_summary`
- `canonical_alignment_count_summary`
- `expected_mode_count_summary`
- `actual_dominant_mode_count_summary`
- `candidate_count_by_symbol`

## 8. 완료 기준

- NAS/XAU/BTC row 모두에서 dominance validation surface가 읽힌다.
- should-have-done 후보와 canonical divergence가 어떤 오류 타입으로 이어지는지 보인다.
- overweighted caution / undervalued continuation evidence가 row-level로 남는다.

## 9. 상태 기준

- `READY`
  - validation row/summary/artifact가 정상 surface됨
- `HOLD`
  - 일부 row만 validation surface가 생성되거나 후보 수가 너무 적음
- `BLOCKED`
  - S4 dominance 또는 canonical field 누락으로 검증 surface 생성 불가
