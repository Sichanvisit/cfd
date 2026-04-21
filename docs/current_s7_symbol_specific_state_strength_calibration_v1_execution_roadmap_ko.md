# S7. Symbol x Direction x Subtype State Strength Calibration v1 실행 로드맵

## 1. 목표

공용 `state strength / dominance` 위에, 심볼별 단일 calibration이 아니라 `심볼 × 방향 × subtype` family를 read-only로 올린다.

## 2. 구현 순서

### S7-1. contract 고정

- `symbol_specific_state_strength_calibration_contract_v1`
- `profile_family_enum_v1`
- `profile_direction_enum_v1`
- `profile_status_enum_v1`
- `profile_match_enum_v1`

### S7-2. registry를 family 구조로 변경

기존:

- `symbol -> single profile`

변경:

- `symbol -> [profile family entries]`

최소 seeded family:

- `NAS100`
  - `UP_CONTINUATION / BREAKOUT_HELD`
  - `DOWN_CONTINUATION / PENDING_REVIEW`
- `XAUUSD`
  - `UP_CONTINUATION / RECOVERY_RECLAIM`
  - `DOWN_CONTINUATION / UPPER_REJECT_REJECTION`
- `BTCUSD`
  - `UP_CONTINUATION / PENDING_REVIEW`
  - `DOWN_CONTINUATION / PENDING_REVIEW`

### S7-3. row matcher 추가

입력:

- `dominant_side`
- `continuation_integrity`
- `reversal_evidence`
- `consumer_veto_tier`
- `few_candle_structure_bias`
- `breakout_hold_quality`
- `body_drive_state`
- `box_state`
- `bb_state`

출력:

- `best profile`
- `profile catalog`
- `profile_match`
- `bias_hint`

### S7-4. runtime/detail surface

`runtime_status.detail.json`에 아래를 유지한다.

- `symbol_specific_state_strength_calibration_contract_v1`
- `symbol_specific_state_strength_calibration_summary_v1`
- `symbol_specific_state_strength_calibration_artifact_paths`

row에는 아래를 추가/유지한다.

- `symbol_state_strength_best_profile_key_v1`
- `symbol_state_strength_profile_family_v1`
- `symbol_state_strength_profile_direction_v1`
- `symbol_state_strength_profile_subtype_v1`
- `symbol_state_strength_profile_status_v1`
- `symbol_state_strength_profile_match_v1`
- `symbol_state_strength_bias_hint_v1`

### S7-5. summary/artifact

- `symbol_specific_state_strength_calibration_latest.json`
- `symbol_specific_state_strength_calibration_latest.md`

summary에는 최소 아래를 포함한다.

- `profile_status_count_summary`
- `profile_match_count_summary`
- `profile_family_count_summary`
- `profile_direction_count_summary`

### S7-6. 테스트

최소 검증:

- NAS up row가 `UP_CONTINUATION / ACTIVE_CANDIDATE / MATCH`
- XAU up row가 `UP_CONTINUATION / ACTIVE_CANDIDATE / MATCH`
- XAU down row가 `DOWN_CONTINUATION / ACTIVE_CANDIDATE / MATCH`
- BTC bear row가 `DOWN_CONTINUATION / SEPARATE_PENDING`
- runtime detail export에 contract/summary/artifact path가 계속 노출

## 3. 현재 적용 범위

- NAS100: 상승 active, 하락 pending
- XAUUSD: 상승 active, 하락 active
- BTCUSD: 상승 pending, 하락 pending

## 4. 다음 단계

1. BTC screenshot/timebox audit 축적
2. NAS down continuation retained window 확보
3. symbol-direction-subtype family를 `should-have-done`와 결합해 calibration error를 추적
4. 충분한 shadow 근거 뒤에만 bias recommendation 확장
