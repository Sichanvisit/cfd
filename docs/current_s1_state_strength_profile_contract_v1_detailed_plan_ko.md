# S1 state_strength_profile_contract_v1 상세 계획

## 1. 목적

`S1`의 목표는 새 해석층의 첫 계약을 고정하는 것이다.

지금 시스템은 이미 많은 상태를 보고 있지만, 그 상태를 최종 우세 해석으로 승격하지 못하고
`wait / reduce / block` 쪽으로 소비하는 장면이 반복된다.

그래서 `S1`은 아래 질문을 같은 언어로 답하게 만든다.

- 지금 기본 방향 가설은 무엇인가
- continuation 구조는 얼마나 살아 있는가
- reversal 직접 증거는 얼마나 강한가
- friction은 얼마나 큰가
- 지금 우세 해석은 continuation인가, boundary인가, reversal risk인가

즉 `S1`은 새 실행 규칙이 아니라, **원인층과 도출층을 분리한 read-only 상태 해석 계약**이다.

## 2. 왜 S1이 필요한가

최근 NAS/XAU/BTC 대조에서 확인한 핵심은 다음과 같다.

- overlay와 HTF, previous box는 이미 강세/약세를 보고 있다
- 그런데 consumer / forecast / belief / barrier는 여전히 caution을 너무 쉽게 소비한다
- 그 결과 runtime은 `BUY_WATCH`인데 execution은 `WAIT` 또는 반대 방향으로 흔들린다

즉 문제는 “못 본다”가 아니라 “본 것을 누구에게 이기게 할 것인가”다.

그래서 첫 단계는 feature를 더 늘리는 것이 아니라, 현재 상태를 공용 계약으로 surface하는 것이다.

## 3. S1 계약 철학

### 3-1. 원인층과 도출층을 분리한다

원인층:

- `trend_pressure`
- `continuation_integrity`
- `reversal_evidence`
- `friction`
- `exhaustion_risk`
- `ambiguity`

도출층:

- `wait_bias_strength`
- `dominance_gap`
- `dominant_side`
- `dominant_mode`
- `caution_level`

중요한 원칙:

- `wait_bias_strength`는 원인 필드가 아니라 도출 필드다
- `dominance_gap`은 `continuation_integrity - reversal_evidence`로 고정한다
- `friction`은 `dominant_side`를 바꾸지 않고 `dominant_mode`와 `caution_level`만 조정한다

### 3-2. 개념 6축, v1 구현 4축

개념 모델은 6축을 유지하되, 첫 구현 우선순위는 아래 4축으로 좁힌다.

- `continuation_integrity`
- `reversal_evidence`
- `friction`
- `dominance_gap`

즉 `trend_pressure`, `exhaustion_risk`, `ambiguity`는 계약에 남기되, 직접 비교 중심축은 한 단계 뒤로 둔다.

### 3-3. side seed를 먼저 정한다

v1 side seed 우선순위:

1. `directional_continuation_overlay_direction`
2. `htf_alignment_state`
3. `previous_box_relation`
4. `previous_box_break_state`

즉 overlay direction이 기본 seed이고, HTF/previous box는 보조 근거다.

## 4. v1 surface 필드

### 4-1. row-level 핵심 필드

- `state_strength_profile_v1`
- `state_strength_side_seed_v1`
- `state_strength_side_seed_source_v1`
- `state_strength_side_seed_confidence_v1`
- `state_strength_trend_pressure_v1`
- `state_strength_continuation_integrity_v1`
- `state_strength_reversal_evidence_v1`
- `state_strength_friction_v1`
- `state_strength_exhaustion_risk_v1`
- `state_strength_ambiguity_v1`
- `state_strength_wait_bias_strength_v1`
- `state_strength_dominance_gap_v1`
- `state_strength_dominant_side_v1`
- `state_strength_dominant_mode_v1`
- `state_strength_caution_level_v1`
- `state_strength_reason_summary_v1`

### 4-2. summary 필드

- `state_strength_summary_v1`
- `state_strength_artifact_paths`

summary는 최소한 아래를 남긴다.

- `side_seed_count_summary`
- `dominant_side_count_summary`
- `dominant_mode_count_summary`
- `caution_level_count_summary`
- `avg_continuation_integrity_v1`
- `avg_reversal_evidence_v1`
- `avg_friction_v1`
- `avg_dominance_gap_v1`

## 5. v1 계산 원칙

### 5-1. continuation_integrity

아래 existing state를 조합해서 계산한다.

- `directional_continuation_overlay_score`
- `htf_alignment_state`
- `previous_box_break_state`
- `previous_box_relation`
- `leg_direction`
- `checkpoint_transition_reason`
- `breakout_candidate_direction`

즉 “기본 방향 seed의 구조가 아직 살아 있는가”를 본다.

### 5-2. reversal_evidence

아래 existing state를 조합한다.

- `consumer_check_side`
- `consumer_check_reason`
- `countertrend_continuation_enabled/action`
- `context_conflict_state`
- `htf_alignment_state`
- `previous_box_break_state`

즉 “불편함”이 아니라 “기존 continuation을 뒤집을 직접 증거”를 surface하는 데 집중한다.

### 5-3. friction

아래 caution 성격 필드를 조합한다.

- `blocked_by`
- `action_none_reason`
- `consumer_check_reason`
- `forecast_state25_candidate_wait_bias_action`
- `belief_candidate_recommended_family`
- `barrier_candidate_recommended_family`
- `late_chase_risk_state`

중요:

- `friction`은 side를 바꾸지 않는다
- `friction`은 continuation을 `CONTINUATION_WITH_FRICTION` 또는 더 높은 `caution_level`로 소비하게 하는 데만 쓰인다

### 5-4. dominance_gap

v1 고정 정의:

- `dominance_gap = continuation_integrity - reversal_evidence`

중요:

- `friction`은 gap 계산에 직접 넣지 않는다
- `ambiguity`는 gap보다 `BOUNDARY`와 `caution_level` 보조 판단에 우선 사용한다

## 6. dominant_mode 기준

v1 후보:

- `CONTINUATION`
- `CONTINUATION_WITH_FRICTION`
- `BOUNDARY`
- `REVERSAL_RISK`

핵심 원칙:

- `friction`은 `dominant_mode`만 조정한다
- `REVERSAL_RISK`는 `reversal_evidence`가 주도해야 한다
- `dominant_side` 변경은 매우 보수적으로 둔다

즉 `upper_reject_confirm` 하나만으로 바로 side reversal이 되면 안 된다.

## 7. 하지 말아야 할 것

- `friction`을 `dominance_gap`에 직접 섞지 않는다
- `wait_bias_strength`를 raw 원인처럼 취급하지 않는다
- single `upper_reject`를 `REVERSAL_OVERRIDE`처럼 쓰지 않는다
- execution/state25를 이 단계에서 직접 바꾸지 않는다
- threshold를 고정 진리처럼 다루지 않는다

## 8. 산출물

문서:

- `current_s1_state_strength_profile_contract_v1_detailed_plan_ko.md`
- `current_s1_state_strength_profile_contract_v1_execution_roadmap_ko.md`

코드:

- `backend/services/state_strength_profile_contract.py`

runtime/detail:

- `state_strength_profile_contract_v1`
- `state_strength_summary_v1`
- `state_strength_artifact_paths`

artifact:

- `data/analysis/shadow_auto/state_strength_summary_latest.json`
- `data/analysis/shadow_auto/state_strength_summary_latest.md`
