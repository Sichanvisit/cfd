# OutcomeLabeler Management Label Rules

## Purpose

This document freezes how each management label is graded against realized trade outcome.

The target is to grade whether the management forecast at anchor time matched what actually happened within the management horizon.

## Shared Rules

- All management labels use `management_horizon_bars = 6`.
- The scoring window is the next `1~6` bars after anchor, capped by earlier position close.
- `label_status` must be `VALID` before a row can become positive or negative.
- If future bars are insufficient, ambiguous, censored, or invalid, the result is `UNKNOWN`.
- Management labels may use hold-vs-cut expectancy, MFE, MAE, TP1 events, opposite-edge events, and reentry improvement as outcome observables.

## `continue_favor_label`

- Positive:
  - holding from anchor stays favorable within horizon
  - same-direction MFE materially exceeds MAE
  - no rapid failure forces early exit
- Negative:
  - adverse excursion dominates within horizon
  - fail-now behavior appears early
  - immediate cut or exit would have been better than hold

## `fail_now_label`

- Positive:
  - the path invalidates quickly after anchor
  - a materially adverse move arrives before favorable extension
  - immediate cut or exit outperforms hold
- Negative:
  - no rapid failure appears
  - hold remains competitive
  - recovery or continuation dominates instead

## `recover_after_pullback_label`

- Positive:
  - an initial wobble or pullback appears after anchor
  - the path later recovers into the original dominant direction
  - holding beats immediate cut within horizon
- Negative:
  - the pullback never recovers meaningfully within horizon
  - cut, exit, or reentry dominates the held path

## `reach_tp1_label`

- Positive:
  - the project's canonical TP1 event is observed within horizon
  - examples:
    - closed trade result marks `tp1_hit`
    - exit log records `Recovery TP1`
    - realized profit satisfies the project's TP1 threshold
- Negative:
  - horizon closes without TP1
  - or the position closes for another reason before TP1 is reached

## `opposite_edge_reach_label`

- Positive:
  - within horizon the realized path reaches the opposite edge implied by the active range or continuation structure
  - examples:
    - wait or exit evaluation marks `reached_opposite_edge == True`
- Negative:
  - the opposite edge is not reached before horizon close or position close

## `better_reentry_if_cut_label`

- Positive:
  - passive hold from anchor is inefficient
  - a later reentry point appears with better realized expectancy
  - cut-plus-reentry outperforms simple hold
- Negative:
  - hold is at least as good as cut-plus-reentry
  - or no materially better reentry point appears within horizon

## Notes

- `continue_favor_label` and `fail_now_label` are the main hold-vs-cut pair.
- `recover_after_pullback_label` and `better_reentry_if_cut_label` are the recovery-vs-reentry pair.
- `reach_tp1_label` uses the project's canonical TP1 event, not an ad hoc offline threshold.
- `opposite_edge_reach_label` is the structural travel rule for range or continuation path completion.
