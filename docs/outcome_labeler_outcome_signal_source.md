# OutcomeLabeler Outcome Signal Source

## Purpose

This document freezes which files and which deterministic join rules the offline `OutcomeLabeler` uses to connect anchor forecasts to realized future outcomes.

## Required Inputs

### Anchor Source

- `entry_decisions.csv`
- Canonical path:
  - `data/trades/entry_decisions.csv`
- Role:
  - anchor forecast row
- Required fields:
  - `symbol`
  - `action`
  - `time`
  - `transition_forecast_v1`
  - `trade_management_forecast_v1`
- Preferred time fields:
  - `signal_bar_ts`
  - `time`
- Supporting bridge fields:
  - `signal_timeframe`
  - `setup_id`
  - `setup_side`

### Primary Future Source

- `trade_closed_history.csv`
- Accepted path candidates:
  - `data/trades/trade_closed_history.csv`
  - `trade_closed_history.csv`
- Role:
  - primary future outcome source
- Required fields:
  - `ticket`
  - `symbol`
  - `direction`
  - `open_time`
  - `open_ts`
  - `close_time`
  - `close_ts`
  - `status`

## Optional Supporting Inputs

- runtime snapshot archive
- position lifecycle log
- exit log

These sources may provide earlier or richer position linkage, but they do not replace the required anchor or closed-trade files.

## Required Join Keys

- `symbol`
- `timestamp`
- `signal_bar_ts`
- `ticket` or `position_id`
- setup / side / action information:
  - `setup_id`
  - `setup_side`
  - `action`

`ticket` or `position_id` is the preferred canonical key. When the anchor row does not already carry it, the labeler must derive a single deterministic position context first, then continue with the canonical position key.

## Deterministic Join Order

### Stage 1: Anchor To Position Context

- Preferred match:
  - exact `ticket` or `position_id` if the anchor row was enriched or an optional bridge source provides it
- Fallback match:
  - same `symbol`
  - aligned `action` / `direction`
  - nearest non-negative `open_ts` or `open_time` from the anchor time
- Supporting fields:
  - `setup_id`
  - `setup_side`
  - `signal_timeframe`
- Tie-break order:
  - smallest non-negative open-time distance from anchor
  - exact action / direction alignment
  - exact setup-side alignment when available
  - latest `open_ts`
  - highest `ticket`

If no candidate is found, use `NO_POSITION_CONTEXT`.

If multiple equal candidates remain after tie-break, use `AMBIGUOUS`.

### Stage 2: Position Context To Closed Outcome

- Preferred match:
  - `ticket` or `position_id` to `trade_closed_history.csv`
- Fallback match:
  - same `symbol`
  - same `direction`
  - resolved `open_ts` or `open_time`
- Tie-break order:
  - exact `ticket` or `position_id`
  - exact `open_ts`
  - smallest absolute open-time distance
  - latest `close_ts`

If no closed trade row is found, use `NO_EXIT_CONTEXT`.

If multiple equal candidates remain after tie-break, use `AMBIGUOUS`.

## Family Usage

### Transition

- Anchor:
  - `entry_decisions.csv` row
- Future window:
  - `horizon_definition_v1.transition`
- Primary observables:
  - future bars after anchor
  - `trade_closed_history.csv` outcome if a position opens or closes inside the transition window

### Management

- Anchor:
  - `entry_decisions.csv` row or resolved live position context
- Future window:
  - `horizon_definition_v1.management`
- Primary observables:
  - `trade_closed_history.csv` close context
  - optional exit or lifecycle logs when management observables need richer context

## Hardening Guidance

- Prefer `signal_bar_ts` over row `time` for anchor alignment.
- Persist `ticket` or `position_id` onto `entry_decisions.csv` when available, without changing the live action gate.
- If neither canonical position keys nor deterministic symbol-side-time bridges are available, exclude the row instead of forcing a join.
