# Forecast FR10 Pre-ML Readiness

## 목적

`Forecast 3갈래`를 나중에 `ML calibration feature`로 안전하게 쓸 수 있게 고정한다.

중요한 원칙:

- `Forecast`는 semantic owner가 아니다.
- `Forecast`는 이미 만들어진 semantic outputs를 해석하는 branch layer다.
- ML이 붙어도 `Forecast`는 `feature_only_not_owner`로만 사용한다.

## 고정 계약

- `forecast_pre_ml_phase = FR10`
- `pre_ml_readiness_contract_v1.contract_version = forecast_pre_ml_readiness_v1`
- `ml_usage_role = feature_only_not_owner`
- `owner_collision_allowed = false`
- `semantic_owner_override_allowed = false`
- `explainable_without_ml = true`

## Branch별 필수 feature

### Transition branch

- `p_buy_confirm`
- `p_sell_confirm`
- `p_reversal_success`
- `p_continuation`
  - 구현 source는 `p_continuation_success`
- `p_false_break`

### Trade management branch

- `p_continue_favor`
- `p_fail_now`
- `p_reach_tp1`
- `p_better_reentry_if_cut`
- `p_recover_after_pullback`

### Gap metrics branch

- `transition_side_separation`
- `transition_confirm_fake_gap`
- `transition_reversal_continuation_gap`
- `management_continue_fail_gap`
- `management_recover_reentry_gap`

## 추천 feature

### Transition

- `edge_turn_success`
  - 구현 source는 `scene_transition_support_v1.p_edge_turn_success`

### Trade management

- `premature_exit_risk`
  - 구현 source는 `management_scene_support_v1.p_premature_exit_risk`

### Gap metrics

- `hold_exit_gap`
- `same_side_flip_gap`

## Runtime에서 보는 위치

### Transition

- `transition_forecast_v1.metadata.forecast_pre_ml_phase`
- `transition_forecast_v1.metadata.pre_ml_readiness_contract_v1`
- `transition_forecast_v1.metadata.pre_ml_required_feature_values_v1`
- `transition_forecast_v1.metadata.pre_ml_recommended_feature_values_v1`

### Trade management

- `trade_management_forecast_v1.metadata.forecast_pre_ml_phase`
- `trade_management_forecast_v1.metadata.pre_ml_readiness_contract_v1`
- `trade_management_forecast_v1.metadata.pre_ml_required_feature_values_v1`
- `trade_management_forecast_v1.metadata.pre_ml_recommended_feature_values_v1`

### Gap metrics

- `forecast_gap_metrics_v1.metadata.forecast_pre_ml_phase`
- `forecast_gap_metrics_v1.metadata.pre_ml_readiness_contract_v1`
- `forecast_gap_metrics_v1.metadata.pre_ml_required_feature_values_v1`
- `forecast_gap_metrics_v1.metadata.pre_ml_recommended_feature_values_v1`

## 의미

이제 `Forecast`는:

- ML 없이도 설명 가능하고
- runtime에서 바로 feature 값을 확인할 수 있고
- 나중에 ML이 붙어도 `semantic owner`를 빼앗기지 않는다.

즉 `FR10`의 핵심은:

`Forecast 3갈래를 학습 feature로는 열어두되, semantic 해석 owner로는 고정해 두는 것`
