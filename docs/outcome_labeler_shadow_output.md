# OutcomeLabeler Shadow Output

## Purpose

This document freezes the review-friendly shadow output generated from one forecast anchor row and its offline outcome labels.

Shadow output answers:

- Which forecast row was graded?
- Which forecast snapshot should be compared against the realized labels?
- What did the transition labels conclude?
- What did the management labels conclude?

## Required Row Type

- `row_type = "outcome_labels_v1"`

The row is a single JSON object that packages the anchor forecast snapshot and the realized outcome labels together.

## Required Sections

Each shadow output row must include:

- `decision_context`
- `forecast_snapshot`
- `outcome_labels_v1`
- `transition_label_summary`
- `management_label_summary`

## Decision Context

`decision_context` should contain the minimum deterministic identity fields needed to inspect the graded row:

- `symbol`
- `action`
- `setup_id`
- `setup_side`
- `time`
- `signal_bar_ts`
- `signal_timeframe`
- `ticket` or `position_id` when available

## Forecast Snapshot

`forecast_snapshot` should preserve the original forecast payloads that were graded:

- `transition_forecast_v1`
- `trade_management_forecast_v1`
- `forecast_gap_metrics_v1` when available

This makes later shadow comparison possible without re-reading the source CSV row.

## Outcome Label Payload

- `outcome_labels_v1` stores the full `OutcomeLabelsV1` bundle.
- `transition_label_summary` condenses transition status, polarity buckets, and review keys.
- `management_label_summary` condenses management status, polarity buckets, and review keys.

The summaries exist for fast human inspection; the nested `outcome_labels_v1` bundle remains the canonical detailed payload.

## Output Targets

Primary output targets:

- `data/analysis`
- `data/datasets/replay_intermediate`

The default review artifact should be easy to inspect under `data/analysis`.

## Future Extension

- Flat comparison columns may be added later for dataset or report-specific consumers.
- Those columns are optional extensions, not part of the minimum L11 contract.
