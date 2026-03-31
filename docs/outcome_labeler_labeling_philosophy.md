# OutcomeLabeler Labeling Philosophy

## Purpose

This document freezes the labeling philosophy for the offline `OutcomeLabeler`.

- `Forecast` answers: "What scenario looks likely now?"
- `OutcomeLabeler` answers: "Was that forecast correct after future bars arrived?"

The two components share the same forecast contract, but their roles are opposite:

- `Forecast` is a present-time scenario score.
- `OutcomeLabeler` is a future-outcome grading layer.

## Core Principles

- A label judges whether the forecast at anchor time matched the realized future outcome.
- A label does not reinterpret the semantic layer.
- A label uses future outcome only.
- A label must carry an explicit horizon.
- A label must separate `transition` labels from `management` labels.
- A label cannot collapse everything into binary only; it must preserve non-scorable states.

## Anchor And Future Source

- Anchor unit: one `entry_decisions.csv` row.
- Future source: `trade_closed_history.csv` plus related future outcome records.
- The labeler reads the anchor-time forecast snapshot and grades it against future realization.

Detailed source inputs and deterministic join rules are frozen in `outcome_signal_source_v1`.

## Positive / Negative / Unknown

Each label produces two things:

- `label_value`: the yes/no answer for the label question when the row is scorable.
- `label_status`: whether the row is scorable at all.

Polarity is interpreted as follows:

- `POSITIVE`: the label-specific success condition happened within the explicit horizon and `label_status == VALID`.
- `NEGATIVE`: the explicit horizon finished without the label-specific success condition and `label_status == VALID`.
- `UNKNOWN`: the row cannot be safely scored into positive or negative.

`UNKNOWN` is not a catch-all synonym for every status string. It is the polarity bucket used when the row is non-scorable.

## Label Status Semantics

- `VALID`: the future path is sufficient and unambiguous, so the row is eligible for positive or negative scoring.
- `INSUFFICIENT_FUTURE_BARS`: the horizon could not be completed because future bars are missing. This maps to `UNKNOWN`.
- `NO_POSITION_CONTEXT`: the anchor row is missing required position context for the label question. This maps to `UNKNOWN`.
- `NO_EXIT_CONTEXT`: the future trade-management or exit context is missing for the label question. This maps to `UNKNOWN`.
- `AMBIGUOUS`: multiple competing future interpretations prevent a unique judgment. This maps to `UNKNOWN`.
- `CENSORED`: the future path is truncated by an external boundary or censoring event. This maps to `UNKNOWN`.
- `INVALID`: the anchor or future outcome is malformed for evaluation. This maps to `UNKNOWN`.

Detailed ambiguity and censoring resolution rules are frozen in `ambiguity_and_censoring_rules_v1`.
Detailed explainability metadata fields and reason blocks are frozen in `label_metadata_v1`.
Review-oriented shadow output shape is frozen in `shadow_label_output_v1`.
Dataset-builder bridge row shape is frozen in `dataset_builder_bridge_v1`.
Validation report shape is frozen in `validation_report_v1`.

## Family Split

### Transition Labels

Transition labels ask:

- Did the predicted transition outcome occur within the transition horizon?

Detailed label-by-label transition scoring rules are frozen in `transition_label_rules_v1`.

Examples:

- `buy_confirm_success_label`
- `sell_confirm_success_label`
- `false_break_label`
- `reversal_success_label`
- `continuation_success_label`

Scoring rule:

- Positive if the transition event occurs within horizon.
- Negative if the transition horizon completes without that event.
- Unknown if the row is insufficient, ambiguous, censored, or invalid.

### Management Labels

Management labels ask:

- Did the predicted trade-management outcome occur within the management horizon?

Detailed label-by-label management scoring rules are frozen in `management_label_rules_v1`.

Examples:

- `continue_favor_label`
- `fail_now_label`
- `recover_after_pullback_label`
- `reach_tp1_label`
- `opposite_edge_reach_label`
- `better_reentry_if_cut_label`

Scoring rule:

- Positive if the management event occurs within horizon.
- Negative if the management horizon completes without that event.
- Unknown if the row is insufficient, ambiguous, censored, or invalid.

## Non-Goals

- No live action gate changes.
- No semantic foundation reinterpretation.
- No observe/confirm rewrite.
- No consumer retuning.
- No immediate model training.

## Implementation

- Offline engine file:
  - `backend/trading/engine/offline/outcome_labeler.py`
- Exported entry points:
  - `build_outcome_labels(...)`
  - `label_transition_outcomes(...)`
  - `label_management_outcomes(...)`
