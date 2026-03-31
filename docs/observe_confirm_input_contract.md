# Observe / Confirm / Action Input Contract

`observe_confirm_input_contract_v2` freezes the canonical inputs allowed to reach the Observe / Confirm / Action router.

## Allowed Semantic Inputs

- `position_snapshot_v2`
- `response_vector_v2`
- `state_vector_v2`
- `evidence_vector_v1`
- `belief_state_v1`
- `barrier_state_v1`

## Allowed Forecast Inputs

- `transition_forecast_v1`
- `trade_management_forecast_v1`
- `forecast_gap_metrics_v1`

## Forbidden Direct Inputs

- `position_vector_v2`
- `response_vector_v1`
- `state_vector_v1`
- `response_raw_snapshot_v1`
- `state_raw_snapshot_v1`
- `energy_snapshot_v1`
- raw detector scores
- legacy rule branches

## Principles

- router reads the canonical semantic bundle only
- router does not directly read raw detector scores
- router does not branch on legacy setup or consumer execution labels
- forecast may modulate routing confidence, but does not replace semantic identity
