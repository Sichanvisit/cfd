# Layer Mode Raw / Effective Dual-Write Freeze

`layer_mode_dual_write_v1` freezes the rule that every mode-addressable semantic layer keeps both `raw` and `effective` outputs.

## Objective

Layer Mode must remain explainable. Even before a dedicated policy overlay is active, replay and logs need a deterministic `effective` payload beside the raw semantic payload so later blocks or suppressions can be traced.

## Canonical Pairs

- `position_snapshot_v2` -> `position_snapshot_effective_v1`
- `response_vector_v2` -> `response_vector_effective_v1`
- `state_vector_v2` -> `state_vector_effective_v1`
- `evidence_vector_v1` -> `evidence_vector_effective_v1`
- `belief_state_v1` -> `belief_state_effective_v1`
- `barrier_state_v1` -> `barrier_state_effective_v1`
- `forecast_features_v1 + transition_forecast_v1 + trade_management_forecast_v1 + forecast_gap_metrics_v1` -> `forecast_effective_policy_v1`

## Trace

`layer_mode_effective_trace_v1` records:

- current effective mode per layer
- raw/effective field pairs
- whether policy overlay was actually applied
- whether effective output is still raw-equivalent

## Principle

Until a stronger overlay is introduced, `effective` may be an identity-preserving bridge copy of `raw`.
That is still useful because it freezes the field names, preserves replay compatibility, and keeps later consumer blocks explainable.
