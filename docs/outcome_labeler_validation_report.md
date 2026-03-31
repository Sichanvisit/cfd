# OutcomeLabeler Validation Report

## Purpose

This document freezes the quality-check report generated from replay dataset rows that already include `outcome_labels_v1`.

The report answers:

- How many labels resolved to positive, negative, or unknown?
- How often do non-scorable statuses appear?
- Is a symbol receiving almost no usable labels?
- Is a label heavily skewed to one side?
- Are unknown or censored rows too common?

## Input

- Input row type: `replay_dataset_row_v1`

## Required Sections

The report must include:

- `transition`
- `management`

## Required Metrics

Each family section must include:

- `label_counts`
- `status_counts`
- `unknown_ratio`
- `censored_ratio`
- `symbol_distribution`
- `horizon_distribution`

## Alerting Goals

The report should make the following issues obvious:

- a symbol receives almost no scorable labels,
- a label is heavily skewed to one side,
- unknown rows are too frequent,
- censored rows are unexpectedly common.

## Default Thresholds

- `high_unknown_ratio_warn = 0.40`
- `high_unknown_ratio_fail = 0.60`
- `label_side_skew_ratio_warn = 0.90`
- `label_side_skew_ratio_fail = 0.98`
- `symbol_min_scorable_rows_warn = 3`

The report must expose the thresholds it used.

## Output

- Primary output directory: `data/analysis`
- Recommended filename prefix: `outcome_label_validation_report_`
