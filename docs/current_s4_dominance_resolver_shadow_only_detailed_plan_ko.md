# S4. Dominance Resolver Shadow-Only 상세 계획

## 1. 목적

S4의 목적은 S1 `state_strength_profile_v1`, S2 `local_structure_profile_v1`,
S3 `runtime_readonly_surface_v1`를 하나의 shadow-only dominance 해석층으로 묶는 것이다.

이 단계는 execution/state25를 바꾸지 않는다.
대신 현재 row가

- continuation 우세인지
- continuation인데 friction이 큰지
- boundary인지
- reversal risk인지

를 `dominance` 언어로 다시 surface하고,
local structure가 충분히 강할 때 caution을 얼마나 할인할 수 있었는지를
`shadow-only`로 기록한다.

## 2. 왜 S4가 필요한가

현재까지의 S1~S3만으로도 많은 정보는 보인다.
하지만 여전히 핵심 질문은 남아 있다.

- continuation 증거와 caution 증거가 같이 있을 때 누가 이기는가
- local structure가 강할 때 기존 caution은 얼마나 과하게 소비되는가
- 지금 WAIT가 합리적인가, 아니면 friction을 reversal처럼 과대해석한 것인가

S4는 바로 이 지점을 겨냥한다.

## 3. 핵심 산출물

### 3-1. Row-level dominance shadow surface

- `state_structure_dominance_profile_v1`
- `dominance_shadow_dominant_side_v1`
- `dominance_shadow_dominant_mode_v1`
- `dominance_shadow_caution_level_v1`
- `dominance_shadow_gap_v1`
- `local_continuation_discount_v1`
- `would_override_caution_v1`
- `dominance_reason_summary_v1`

### 3-2. Detail payload surface

- `state_structure_dominance_contract_v1`
- `state_structure_dominance_summary_v1`
- `state_structure_dominance_artifact_paths`

## 4. 결정 원칙

### 4-1. dominance_gap

v1에서 중심 비교 필드는

- `dominance_gap = continuation_integrity - reversal_evidence`

이다.

`friction`은 gap 계산에 직접 넣지 않는다.

### 4-2. local continuation discount

local structure가 continuation을 강하게 지지할 때만
`friction`과 `wait_bias_strength`의 실효값을 제한적으로 할인한다.

할인 가능 조건 예:

- bull seed:
  - `few_candle_higher_low_state_v1 in {HELD, CLEAN_HELD}`
  - `breakout_hold_quality_v1 in {STABLE, STRONG}`
  - `body_drive_state_v1 in {WEAK_DRIVE, STRONG_DRIVE}`
- bear seed:
  - `few_candle_lower_high_state_v1 in {HELD, CLEAN_HELD}`
  - `breakout_hold_quality_v1 in {STABLE, STRONG}`
  - `body_drive_state_v1 in {WEAK_DRIVE, STRONG_DRIVE}`

추가 제한:

- `state_strength_reversal_evidence_v1`가 높으면 discount 금지
- `consumer_veto_tier_v1 = REVERSAL_OVERRIDE`이면 discount 금지

### 4-3. discount 금지선

`local_continuation_discount_v1`는

- `friction`
- `wait_bias_strength`

의 실효값만 줄일 수 있다.

다음은 절대 건드리면 안 된다.

- `reversal_evidence`
- structure break 판정
- `consumer_veto_tier_v1 = REVERSAL_OVERRIDE`

### 4-4. dominant side / mode

S4의 dominant side는 기본적으로 S1 `state_strength_dominant_side_v1`를 따른다.
단, `REVERSAL_OVERRIDE`와 reversal structure가 함께 강하게 확인된 경우만
반대 side 후보를 shadow-only로 surface할 수 있다.

dominant mode는 아래 네 가지 중 하나다.

- `CONTINUATION`
- `CONTINUATION_WITH_FRICTION`
- `BOUNDARY`
- `REVERSAL_RISK`

## 5. would_override_caution_v1

이 필드는 shadow-only recommendation이다.

`True` 조건 예:

- `consumer_veto_tier_v1 = FRICTION_ONLY`
- `dominance_gap`이 continuation 우세
- `local_continuation_discount_v1 >= small_threshold`
- `reversal_evidence`는 낮음

해석:

- "현재 caution은 완전히 틀린 건 아니지만,
  local continuation이 강해서 caution의 실효 강도를 더 낮출 수 있었다"

## 6. summary artifact

최소 포함:

- `symbol_count`
- `surface_ready_count`
- `dominant_side_count_summary`
- `dominant_mode_count_summary`
- `caution_level_count_summary`
- `would_override_caution_count_summary`
- `discount_applied_count_summary`

## 7. 완료 기준

- NAS/XAU/BTC row 모두에서 dominance shadow contract가 surface된다.
- `continuation with friction`과 `reversal risk`가 구분되어 보인다.
- `local_continuation_discount_v1`와 `would_override_caution_v1`가 shadow-only로 읽힌다.

## 8. 상태 기준

- `READY`
  - 세 심볼 모두 dominance shadow row/summary가 정상 surface됨
- `HOLD`
  - 일부 row만 dominance surface가 생기거나, summary freshness가 흔들림
- `BLOCKED`
  - runtime payload 충돌, S1~S3 field 누락, 또는 dominance surface 생성 실패
