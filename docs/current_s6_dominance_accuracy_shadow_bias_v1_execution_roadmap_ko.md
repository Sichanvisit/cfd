# S6. Dominance Accuracy / Shadow Bias V1 실행 로드맵

## 1. 목표

S6는 S5 dominance validation을 기반으로

- proxy accuracy surface
- shadow-only dominance bias recommendation

을 추가하는 단계다.

이 단계에서도 execution/state25는 바꾸지 않는다.

## 2. 구현 순서

### S6-1. contract/service 추가

- `dominance_accuracy_shadow_contract_v1`
- row builder:
  - `build_dominance_accuracy_shadow_row_v1(...)`
- attach helper:
  - `attach_dominance_accuracy_shadow_fields_v1(...)`
- combined report writer

### S6-2. proxy accuracy 계산

row-level:

- `dominance_over_veto_flag_v1`
- `dominance_under_veto_flag_v1`
- `dominance_friction_separation_state_v1`
- `dominance_boundary_dwell_risk_v1`

summary:

- `over_veto_rate`
- `under_veto_rate`
- `friction_separation_quality`
- `boundary_dwell_quality`

### S6-3. shadow bias 계산

row-level:

- `dominance_shadow_bias_candidate_state_v1`
- `dominance_shadow_bias_effect_v1`
- `dominance_shadow_bias_confidence_v1`
- `dominance_shadow_bias_reason_v1`
- `dominance_shadow_would_change_execution_v1`
- `dominance_shadow_would_change_state25_v1`

summary:

- `dominance_candidate_shadow_report_v1`

### S6-4. pending status field 추가

아직 hindsight join이 안 된 항목은 summary에 pending 상태로 남긴다.

- `future_outcome_join_status_v1 = PENDING`
- `discount_comparison_status_v1 = PENDING`
- `guard_promotion_alignment_status_v1 = PENDING`

### S6-5. trading_application 연결

순서:

1. S5 dominance validation
2. S6 dominance accuracy / shadow bias

detail payload export:

- `dominance_accuracy_shadow_contract_v1`
- `dominance_accuracy_summary_v1`
- `dominance_candidate_shadow_report_v1`
- `dominance_accuracy_shadow_artifact_paths`

### S6-6. 테스트 고정

최소 테스트:

- continuation underpromoted -> over-veto + raise continuation
- friction misread as reversal -> misread + raise continuation
- true reversal missed -> under-veto + lower continuation
- aligned -> keep neutral
- runtime status export smoke
- artifact write smoke

## 3. 완료 기준

- 세 심볼 모두 S6 row field가 보인다.
- proxy accuracy summary와 shadow report가 같이 생성된다.
- pending status field도 같이 보인다.

## 4. 상태 기준

- `READY`
  - row/detail/artifact 정상
- `HOLD`
  - candidate 적음 또는 hindsight pending
- `BLOCKED`
  - S5 누락 또는 payload 충돌
