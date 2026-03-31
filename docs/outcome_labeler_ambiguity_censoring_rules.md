# OutcomeLabeler Ambiguity And Censoring Rules

## Purpose

This document freezes when the labeler must refuse to emit a forced binary label.

The goal is simple:

- do not pollute the dataset with unsafe `0/1` labels
- prefer exclusion over noisy supervision

## Mandatory Non-Scorable Statuses

- `INSUFFICIENT_FUTURE_BARS`
- `NO_EXIT_CONTEXT`
- `NO_POSITION_CONTEXT`
- `AMBIGUOUS`
- `CENSORED`

## Resolution Principles

- Do not force a binary label when the row is not safely scorable.
- Only `VALID` rows may emit positive or negative label values.
- If multiple non-scorable conditions apply, use status precedence.
- Excluding an uncertain row is better than injecting noisy supervision.

## Status Precedence

- `INVALID`
- `NO_POSITION_CONTEXT`
- `CENSORED`
- `INSUFFICIENT_FUTURE_BARS`
- `NO_EXIT_CONTEXT`
- `AMBIGUOUS`
- `VALID`

## Status Rules

### `INSUFFICIENT_FUTURE_BARS`

- Use when:
  - future bars do not fully cover the required horizon
  - and there is no earlier legitimate boundary that closes the question
- Examples:
  - only `2` future bars exist for a `6` bar management horizon
  - the next `1~3` transition bars are not fully available yet

### `NO_EXIT_CONTEXT`

- Use when:
  - exit, close, TP1, or closed-trade observables are required
  - but cannot be linked even though the future window is otherwise present
- Examples:
  - position close log is missing
  - TP1 label requires canonical TP1 evidence but no exit-side observable is available

### `NO_POSITION_CONTEXT`

- Use when:
  - the anchor row cannot be linked to the required live-position or open-position context
- Examples:
  - open and close cannot be joined to the anchor
  - management anchor cannot confirm a live position existed at that time

### `AMBIGUOUS`

- Use when:
  - positive and negative interpretations both remain materially plausible
  - or competing sources disagree
  - or no unique judgment can be made
- Examples:
  - positive and negative path evidence are both satisfied within horizon
  - multiple candidate joins or conflicting future sources exist

### `CENSORED`

- Use when:
  - future path is truncated by an external interruption before safe scoring
- Examples:
  - mid-window data gap
  - export cutoff
  - dataset end
  - continuity break before the label can be judged safely

## Family Notes

- Transition:
  - `INSUFFICIENT_FUTURE_BARS` is common when the `1~3` bar window is incomplete.
  - `AMBIGUOUS` is common when confirm, fake, reversal, and continuation compete without a unique winner.
- Management:
  - `NO_EXIT_CONTEXT` is common when TP1, close, or realized management outcome cannot be linked.
  - `CENSORED` is common when the `1~6` bar management path is interrupted before hold, cut, recovery, or reentry can be judged.

## Label Action

- For every non-scorable status:
  - set `label_value = None`
  - map polarity to `UNKNOWN`
  - exclude the row from binary training and calibration score sets
