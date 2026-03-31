# OutcomeLabeler Transition Label Rules

## Purpose

This document freezes how each transition label is graded against realized future outcome.

The target is not to reinterpret the semantic layer.
The target is to grade whether the transition forecast at anchor time matched what actually happened within the transition horizon.

## Shared Rules

- All transition labels use `transition_horizon_bars = 3`.
- The scoring window is the next `1~3` bars after anchor.
- `label_status` must be `VALID` before a row can become positive or negative.
- If future bars are insufficient, ambiguous, censored, or invalid, the result is `UNKNOWN`.

## `buy_confirm_success_label`

- Positive:
  - `BUY_CONFIRM` lifecycle appears within horizon
  - or equivalent buy-side action continuation remains live
  - or realized buy-side outcome reaches the favorable threshold within horizon
- Negative:
  - predicted buy confirm is invalidated within horizon
  - or it flips quickly into fake / failed-confirm behavior
  - or opposite-side dominance overtakes the buy path

## `sell_confirm_success_label`

- Positive:
  - `SELL_CONFIRM` lifecycle appears within horizon
  - or equivalent sell-side action continuation remains live
  - or realized sell-side outcome reaches the favorable threshold within horizon
- Negative:
  - predicted sell confirm is invalidated within horizon
  - or it flips quickly into fake / failed-confirm behavior
  - or opposite-side dominance overtakes the sell path

## `false_break_label`

- Positive:
  - projected break / reclaim / reject is invalidated quickly within horizon
  - continuation or confirm cannot hold
  - structure returns rapidly or opposite signal takes over
- Negative:
  - projected break or continuation remains valid through horizon
  - no quick invalidation occurs
  - confirm path keeps control instead of reverting

## `reversal_success_label`

- Positive:
  - reversal forecast leads to meaningful opposite-direction extension within horizon
  - middle reclaim or edge reject is followed by directional follow-through against the prior move
- Negative:
  - opposite-direction extension does not materialize within horizon
  - continuation, stall, or rejection of the reversal dominates instead

## `continuation_success_label`

- Positive:
  - continuation forecast leads to meaningful same-direction extension within horizon
  - break or hold structure remains intact
- Negative:
  - continuation structure fails, stalls, or reverses within horizon
  - same-direction follow-through does not stay above the success threshold
  - reversal or false-break behavior overtakes the continuation path

## Notes

- `buy_confirm_success_label` and `sell_confirm_success_label` are directional confirm rules.
- `false_break_label` is the quick invalidation rule.
- `reversal_success_label` and `continuation_success_label` grade directional path quality after the initial transition setup.
