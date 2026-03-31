# OutcomeLabeler Label Metadata

## Purpose

This document freezes the explainability metadata that accompanies each offline outcome label family.

Metadata answers:

- Which contract produced the label?
- Which anchor and future window were used?
- Which source rows were matched?
- Why did each label resolve to positive, negative, or unknown?

## Required Family Metadata Fields

Each `TransitionOutcomeLabelsV1.metadata` and `TradeManagementOutcomeLabelsV1.metadata` payload must include:

- `label_contract`
- `labeler_version`
- `anchor_timestamp`
- `horizon_bars`
- `future_window_start`
- `future_window_end`
- `source_files`
- `matched_outcome_rows`
- `label_reasons`
- `label_status_reason`

## Source Traceability

- `source_files` must identify the anchor source and future outcome source candidates.
- `matched_outcome_rows` must identify which position context, closed trade context, and future bars were actually used.
- If a deterministic join could not be completed, the metadata must still show the failed match method so the row can be audited.

## Per-Label Reason Blocks

`label_reasons` is a dictionary keyed by label field name.

Each reason block must contain:

- `reason_code`
- `reason_text`
- `evidence`

Recommended behavior:

- `reason_code` is a compact machine-friendly explanation key.
- `reason_text` is the short human explanation.
- `evidence` contains the small set of metrics or matched-row facts that justify the result.

## Label Status Reason

- `label_status_reason` must explain why the family is `VALID`, `INSUFFICIENT_FUTURE_BARS`, `NO_POSITION_CONTEXT`, `NO_EXIT_CONTEXT`, `AMBIGUOUS`, `CENSORED`, or `INVALID`.
- For non-scorable rows, `label_status_reason` is required and should be the primary explanation for why all label values are `None`.
- `label_status_reason` should use the same `reason_code` / `reason_text` / `evidence` shape as per-label reasons.

## Example Shape

```python
{
    "label_contract": "TransitionOutcomeLabelsV1",
    "labeler_version": "outcome_labeler_engine_v1",
    "anchor_timestamp": 1773149400,
    "horizon_bars": 3,
    "future_window_start": 1773149460,
    "future_window_end": 1773149640,
    "source_files": {
        "anchor": ["data/trades/entry_decisions.csv"],
        "future_outcome": ["data/trades/trade_closed_history.csv", "trade_closed_history.csv"],
        "optional": ["runtime_snapshot_archive", "position_lifecycle_log", "exit_log"],
    },
    "matched_outcome_rows": {
        "position_context": {"position_key": 7001, "match_method": "exact_position_key"},
        "closed_trade_context": {"position_key": 7001, "match_method": "exact_position_key"},
        "future_bars": {"count": 3, "timestamps": [1773149460, 1773149520, 1773149580]},
    },
    "label_status_reason": {
        "reason_code": "valid_complete_horizon",
        "reason_text": "Future window covered the required transition horizon and yielded a unique outcome.",
        "evidence": {"future_bar_count": 3, "horizon_bars": 3},
    },
    "label_reasons": {
        "buy_confirm_success_label": {
            "reason_code": "same_side_confirmation_observed",
            "reason_text": "Buy side stayed dominant through the 3-bar transition window with no early invalidation.",
            "evidence": {"dominant_side": "BUY", "bullish_move_ratio": 0.012},
        },
    },
}
```
