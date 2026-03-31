# Observe / Confirm / Action Output Contract

`observe_confirm_output_contract_v2` freezes the canonical output shape of `ObserveConfirmSnapshot`.

During migration, `observe_confirm_v2` is the canonical output field and `observe_confirm_v1` remains the compatibility dual-write field.

## Required Fields

- `state`
- `action`
- `side`
- `confidence`
- `reason`
- `archetype_id`
- `invalidation_id`
- `management_profile_id`
- `metadata`

## Lifecycle State Values

- `OBSERVE`
- `CONFIRM`
- `CONFLICT_OBSERVE`
- `NO_TRADE`
- `INVALIDATED`

## Action / Side Values

- `action`: `WAIT`, `BUY`, `SELL`, `NONE`
- `side`: `BUY`, `SELL`, `""`

## Canonical Archetypes

- `upper_reject_sell`
- `upper_break_buy`
- `lower_hold_buy`
- `lower_break_sell`
- `mid_reclaim_buy`
- `mid_lose_sell`

## Canonical Invalidations

- `upper_reject_sell -> upper_break_reclaim`
- `upper_break_buy -> breakout_failure`
- `lower_hold_buy -> lower_support_fail`
- `lower_break_sell -> breakdown_failure`
- `mid_reclaim_buy -> mid_relose`
- `mid_lose_sell -> mid_reclaim`

## Canonical Management Profiles

- `upper_reject_sell -> reversal_profile`
- `upper_break_buy -> breakout_hold_profile`
- `lower_hold_buy -> support_hold_profile`
- `lower_break_sell -> breakdown_hold_profile`
- `mid_reclaim_buy -> mid_reclaim_fast_exit_profile`
- `mid_lose_sell -> mid_lose_fast_exit_profile`

## Metadata Required Fields

- `raw_contributions`
- `effective_contributions`
- `winning_evidence`
- `blocked_reason`

## Principles

- `state` is routing lifecycle only
- `archetype_id` is canonical trade identity
- `invalidation_id` is canonical invalidation identity aligned to `archetype_id`
- `management_profile_id` is canonical consumer and exit handoff identity aligned to `archetype_id`
- `confidence` is an execution readiness score, not a probability
- `Forecast` may modulate `confidence` and `confirm/wait` only
- `Forecast` may not redefine `archetype_id` or flip `side`
- `state` carries lifecycle only; legacy pattern names move to `archetype_id`
- `archetype_id` is canonical entry identity, not setup name and not lifecycle state
- `WAIT + BUY/SELL side` is allowed as directional observe
- `NONE + ""` is reserved for no-trade output
- metadata must always carry the normalized required keys even when values are empty
