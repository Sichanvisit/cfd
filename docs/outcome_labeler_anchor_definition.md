# OutcomeLabeler Anchor Definition

## Purpose

This document freezes what row and what anchor time each label family uses for scoring.

Anchor definition answers:

- Which row is the scoring reference?
- Which timestamp on that row is the anchor time?
- Which future interval starts from that anchor?

## Shared Rules

- `transition` and `management` labels use distinct anchor rules.
- The same `entry_decisions.csv` row may feed both families.
- Even when the same row is reused, the label rules remain family-specific.
- `signal_bar_ts` is the preferred anchor timestamp when available.
- The row `time` field is the fallback anchor timestamp.

## Shared Anchor Basis

- Primary source row: `entry_decisions.csv`
- Primary row unit: one decision row
- Preferred timestamp priority:
  - `signal_bar_ts`
  - `time`
- Preferred timeframe field:
  - `signal_timeframe`

## Transition Anchor

- Anchor row:
  - `entry_decisions.csv` row
- Anchor time:
  - `signal_bar_ts` if present
  - otherwise row `time`
- Forecast field being scored:
  - `transition_forecast_v1`
- Future interval:
  - starts at the first future bar after anchor time
  - ends when the transition horizon closes
  - evaluates the next `1~3` bars after anchor
- Scoring purpose:
  - determine whether the `TransitionForecast` was correct within the future transition window

## Management Anchor

- Preferred anchor row:
  - `entry_decisions.csv` row
- Alternate anchor row:
  - actual position open event row
- Anchor time:
  - `signal_bar_ts` if present
  - otherwise row `time`
  - if the alternate open-event row is used later, use that event time
- Forecast field being scored:
  - `trade_management_forecast_v1`
- Future interval:
  - starts from the anchor time while the position is live
  - ends when the management horizon closes or the position closes
  - evaluates the next `1~6` bars after anchor, capped by earlier position close
- Scoring purpose:
  - determine whether hold / fail / recover / tp1 / reentry style forecasts were correct

## Supporting Result Sources

- `trade_closed_history.csv`
- position log
- exit log
- closed trade result

Detailed source selection and deterministic join order are frozen in `outcome_signal_source_v1`.

## Notes

- Existing historical rows may lack `signal_bar_ts`; those rows fall back to the row timestamp.
- New rows should persist `signal_bar_ts` and `signal_timeframe` when available so offline scoring can anchor to the signal bar directly.
- Transition horizon is fixed to the next `1~3` bars after anchor.
- Management horizon is fixed to the next `1~6` bars after anchor, capped by earlier position close when applicable.
