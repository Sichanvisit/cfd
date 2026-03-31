# OutcomeLabeler Dataset Builder Bridge

## Purpose

This document freezes the row-level bridge between the offline `OutcomeLabeler` and the future replay dataset builder.

The bridge row lets one anchor decision row carry:

- the raw decision row,
- parsed semantic snapshots,
- parsed forecast snapshots,
- realized outcome labels,

all under the same deterministic row key.

## Required Row Type

- `row_type = "replay_dataset_row_v1"`

## Row Key

Each replay dataset row must use one deterministic `row_key`.

The key is derived from:

- `symbol`
- `anchor_time_field`
- `anchor_time_value`
- `action`
- `setup_id`
- `ticket` or `position_id`

The exact string encoding may vary, but the same anchor row must always generate the same row key.

## Required Sections

Each row must include:

- `decision_row`
- `semantic_snapshots`
- `forecast_snapshots`
- `outcome_labels_v1`

## Semantic Snapshots

The semantic section contains the parsed semantic-family payloads needed by a replay dataset:

- `position_snapshot_v2`
- `response_raw_snapshot_v1`
- `response_vector_v2`
- `state_raw_snapshot_v1`
- `state_vector_v2`
- `evidence_vector_v1`
- `belief_state_v1`
- `barrier_state_v1`
- `observe_confirm_v1`

## Forecast Snapshots

The forecast section contains the parsed forecast-family payloads needed by a replay dataset:

- `forecast_features_v1`
- `transition_forecast_v1`
- `trade_management_forecast_v1`
- `forecast_gap_metrics_v1`

## Builder Handoff

- The bridge row is the minimum handoff contract for `backend/trading/engine/offline/replay_dataset_builder.py`.
- Batch orchestration can be added later, but row extraction should not need to be redesigned once this contract is fixed.
- The same row key must join all four sections without additional heuristics.
