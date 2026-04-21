# S3. Runtime Read-Only Surface V1 상세 계획

## 1. 목적

S3의 목적은 S1 `state_strength_profile_v1`와 S2 `local_structure_profile_v1`를
실제 runtime row에서 같은 read-only 해석 surface로 묶는 것이다.

이 단계는 execution이나 state25를 바꾸는 단계가 아니다.
오직 현재 row가

- continuation 우세인지
- continuation인데 friction이 큰지
- boundary인지
- reversal 쪽 경계가 커졌는지

를 공통 field로 읽히게 만드는 단계다.

## 2. 왜 별도 S3가 필요한가

S1/S2만으로도 각 row에는 이미 개별 field가 존재한다.
하지만 현재 운영 관점에서 필요한 것은 개별 점수/상태 나열이 아니라
`consumer veto`가 어떤 tier로 해석돼야 하는지를 같은 runtime 언어로 읽는 것이다.

즉 지금 문제는 "field가 없다"가 아니라
"기존 field를 어떤 read-only tier로 묶어 읽어야 하는가"가 비어 있다는 데 있다.

S3는 이 공백을 메운다.

## 3. 핵심 산출물

### 3-1. Row-level read-only surface

- `state_strength_profile_v1`
- `local_structure_profile_v1`
- `consumer_veto_tier_v1`
- `consumer_veto_reason_summary_v1`
- `runtime_readonly_surface_v1`

### 3-2. Detail payload surface

- `runtime_readonly_surface_contract_v1`
- `runtime_readonly_surface_summary_v1`
- `runtime_readonly_surface_artifact_paths`

## 4. consumer_veto_tier_v1 계약

### enum

- `FRICTION_ONLY`
- `BOUNDARY_WARNING`
- `REVERSAL_OVERRIDE`

### 해석 원칙

#### FRICTION_ONLY

- dominant side는 유지된다.
- 현재 caution은 방향 반전이 아니라 진입/추격 품질 악화에 가깝다.
- `CONTINUATION_WITH_FRICTION`와 가장 잘 맞는 tier다.

#### BOUNDARY_WARNING

- continuation과 reversal 증거가 혼재한다.
- local structure가 continuation favor까지는 아니고 mixed에 가깝다.
- WAIT가 합리적일 수 있는 경계 상태다.

#### REVERSAL_OVERRIDE

- 기존 continuation 우세를 뒤집을 정도의 reversal evidence가 확인된다.
- structure break, failed hold, counter drive 같은 증거가 같이 있어야 한다.
- 단일 `upper_reject`, `soft_block`, `wait_bias`만으로는 허용되지 않는다.

## 5. v1 판정 기준

### REVERSAL_OVERRIDE 후보

다음이 같이 보일 때만 허용한다.

- `state_strength_dominant_mode_v1 = REVERSAL_RISK`
  또는 `state_strength_reversal_evidence_v1`가 충분히 높음
- `few_candle_structure_bias_v1 = REVERSAL_FAVOR`
  또는 `breakout_hold_quality_v1 = FAILED`
- `body_drive_state_v1 = COUNTER_DRIVE`
  또는 continuation integrity가 낮음

### BOUNDARY_WARNING 후보

다음이 보이면 boundary warning으로 본다.

- `state_strength_dominant_mode_v1 = BOUNDARY`
- `few_candle_structure_bias_v1 = MIXED`
- `breakout_hold_quality_v1 = WEAK`
- `state_strength_caution_level_v1 = HIGH`

### FRICTION_ONLY 후보

다음은 side를 뒤집지 않고 friction-only로 본다.

- `state_strength_dominant_mode_v1 = CONTINUATION_WITH_FRICTION`
- `consumer_check_reason`이 `upper_reject*`, `outer_band_reversal_support_required_observe` 계열
- `blocked_by = energy_soft_block` 등 소프트 차단
- local structure는 아직 continuation favor 또는 최소 mixed

## 6. 출력 설계

### runtime_readonly_surface_v1

최소 포함 field:

- `contract_version`
- `state_strength_dominant_side_v1`
- `state_strength_dominant_mode_v1`
- `state_strength_dominance_gap_v1`
- `few_candle_structure_bias_v1`
- `breakout_hold_quality_v1`
- `body_drive_state_v1`
- `consumer_veto_tier_v1`
- `consumer_veto_reason_summary_v1`
- `execution_change_allowed = false`
- `state25_change_allowed = false`

## 7. summary artifact

요약은 최소 아래를 포함한다.

- `symbol_count`
- `surface_ready_count`
- `consumer_veto_tier_count_summary`
- `dominant_side_count_summary`
- `dominant_mode_count_summary`
- `structure_bias_count_summary`

## 8. 완료 기준

- NAS/XAU/BTC row 모두에 같은 read-only contract가 붙는다.
- `continuation with friction`과 `reversal override`가 서로 다른 tier로 구분된다.
- runtime payload 과부하 없이 detail payload와 artifact가 갱신된다.

## 9. 상태 기준

- `READY`
  - 세 심볼 모두 `consumer_veto_tier_v1`와 runtime read-only surface가 정상 surface됨
- `HOLD`
  - 일부 row는 surface되지만 일부 row는 field 누락 또는 contract 누락
- `BLOCKED`
  - runtime payload 오류, summary artifact 누락, 또는 기존 S1/S2 profile과 충돌 발생
