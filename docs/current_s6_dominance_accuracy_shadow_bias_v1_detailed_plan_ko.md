# S6. Dominance Accuracy / Shadow Bias V1 상세 계획

## 1. 목적

S6의 목적은 S5 dominance validation 결과를 바탕으로

- `dominance accuracy`를 proxy 지표로 요약하고
- `dominance shadow bias`를 read-only recommendation으로 남기며
- 이후 20-bar hindsight join, discount 비교, guard/promotion 정합 검증으로 확장할 준비를 갖추는 것이다.

이 단계에서도 execution/state25는 바꾸지 않는다.

## 2. 왜 proxy 단계가 필요한가

로드맵상 최종적으로 보고 싶은 것은

- `dominance_gap vs 20-bar direction`
- `discount 적용/미적용 비교`
- `guard/promotion 정합`

이지만, 현재는 아직 이 전체 hindsight join이 다 연결된 상태가 아니다.

그래서 S6 v1에서는 먼저

- S5 `dominance_error_type_v1`
- S5 `dominance_should_have_done_candidate_v1`
- canonical alignment
- session bucket

을 바탕으로 proxy accuracy와 shadow bias를 surface한다.

즉 v1은 **proxy readiness surface**, full hindsight accuracy는 후속 확장이다.

## 3. 핵심 산출물

### 3-1. Row-level surface

- `dominance_accuracy_shadow_profile_v1`
- `dominance_over_veto_flag_v1`
- `dominance_under_veto_flag_v1`
- `dominance_friction_separation_state_v1`
- `dominance_boundary_dwell_risk_v1`
- `dominance_shadow_bias_candidate_state_v1`
- `dominance_shadow_bias_effect_v1`
- `dominance_shadow_bias_confidence_v1`
- `dominance_shadow_bias_reason_v1`
- `dominance_shadow_would_change_execution_v1`
- `dominance_shadow_would_change_state25_v1`

### 3-2. Detail payload surface

- `dominance_accuracy_shadow_contract_v1`
- `dominance_accuracy_summary_v1`
- `dominance_candidate_shadow_report_v1`
- `dominance_accuracy_shadow_artifact_paths`

## 4. Proxy accuracy 정의

### 4-1. over-veto

다음 error type은 over-veto로 본다.

- `CONTINUATION_UNDERPROMOTED`
- `REVERSAL_OVERCALLED`
- `FRICTION_MISREAD_AS_REVERSAL`
- `BOUNDARY_STAYED_TOO_LONG`

### 4-2. under-veto

다음 error type은 under-veto로 본다.

- `TRUE_REVERSAL_MISSED`

### 4-3. friction separation quality

friction separation은

- expected mode가 `CONTINUATION_WITH_FRICTION`일 때
- actual dominance mode가 정말 `CONTINUATION_WITH_FRICTION`로 유지됐는지

를 기준으로 본다.

row-level state:

- `SEPARATED`
- `MISREAD_AS_REVERSAL`
- `MIXED`
- `NOT_APPLICABLE`

### 4-4. boundary dwell risk

`dominance_error_type_v1 = BOUNDARY_STAYED_TOO_LONG`
이면 boundary dwell risk를 켠다.

## 5. Shadow bias effect 정의

### 5-1. raise continuation confidence

다음은 continuation confidence를 높여볼 가치가 있는 경우다.

- `CONTINUATION_UNDERPROMOTED`
- `FRICTION_MISREAD_AS_REVERSAL`
- `BOUNDARY_STAYED_TOO_LONG`
- `REVERSAL_OVERCALLED`

효과:

- `RAISE_CONTINUATION_CONFIDENCE`

### 5-2. lower continuation confidence

다음은 continuation confidence를 낮춰볼 가치가 있는 경우다.

- `TRUE_REVERSAL_MISSED`

효과:

- `LOWER_CONTINUATION_CONFIDENCE`

### 5-3. keep neutral

- `ALIGNED`
- 충분한 근거가 없는 경우

효과:

- `KEEP_NEUTRAL`

## 6. confidence 원칙

- `HIGH`
  - `FRICTION_MISREAD_AS_REVERSAL`
  - `TRUE_REVERSAL_MISSED`
- `MEDIUM`
  - 나머지 READY candidate
- `LOW`
  - `KEEP_NEUTRAL`

## 7. summary artifact

### dominance_accuracy_summary_v1

최소 포함:

- `symbol_count`
- `candidate_count`
- `over_veto_rate`
- `under_veto_rate`
- `friction_separation_quality`
- `boundary_dwell_quality`
- `candidate_count_by_session`
- `future_outcome_join_status_v1`
- `discount_comparison_status_v1`
- `guard_promotion_alignment_status_v1`

### dominance_candidate_shadow_report_v1

최소 포함:

- `candidate_state_count_summary`
- `effect_count_summary`
- `candidate_count_by_session`
- `symbol_count`
- `execution_change_allowed = false`
- `state25_change_allowed = false`

## 8. 완료 기준

- NAS/XAU/BTC row 모두에서 proxy accuracy와 shadow bias field가 보인다.
- over-veto / under-veto / friction separation / boundary dwell이 summary로 읽힌다.
- shadow bias effect가 row/detail/artifact로 남는다.

## 9. 상태 기준

- `READY`
  - proxy accuracy / shadow bias row/summary/artifact 정상 surface
- `HOLD`
  - row는 있으나 candidate 표본이 적거나 hindsight join status가 pending
- `BLOCKED`
  - S5 validation 누락
  - runtime payload 충돌
  - summary artifact 생성 실패
