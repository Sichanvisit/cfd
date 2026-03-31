# OutcomeLabeler Horizon Definition

## Purpose

This document freezes how far into the future each label family is allowed to look.

Horizon definition answers:

- When does the future window start?
- How many bars are allowed for scoring?
- When does the window close?

## Shared Rules

- Every label uses an explicit future window.
- The future window starts on bar `1` after the anchor.
- `transition` and `management` use different window lengths.
- `management` stays capped even if the position remains open beyond the default bar limit.

## Transition Horizon

- Family:
  - `transition`
- Window:
  - next `1~3` bars after anchor
- Start:
  - first future bar after anchor
- End:
  - bar `3` after anchor
- Horizon bars:
  - `3`
- Why:
  - transition labels judge fast confirm / fake / reversal / continuation outcomes

## Management Horizon

- Family:
  - `management`
- Window:
  - next `1~6` bars after anchor
  - or earlier position close
- Start:
  - first future bar after anchor while position context is live
- End:
  - bar `6` after anchor
  - or position close if it happens earlier
- Horizon bars:
  - `6`
- Why:
  - management labels need a longer hold / cut / recover / tp1 / reentry evaluation window

## Recommended Metadata

- `transition_horizon_bars = 3`
- `management_horizon_bars = 6`

## Scoring Notes

- A positive label may resolve before the final horizon bar if its success event occurs early.
- A negative label requires the relevant horizon to finish without the success event.
- If the required future window cannot be observed, use `INSUFFICIENT_FUTURE_BARS`.
