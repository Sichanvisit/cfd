# Entry Guard Contract

`entry_guard_contract_v1` freezes canonical consumer block reasons.

## Separation

- semantic non-action means no executable action was produced from observe-confirm or preflight meaning
- execution block means an otherwise actionable handoff was blocked by runtime guards

## Canonical Semantic Reasons

- `observe_confirm_missing`
- `preflight_no_trade`
- `preflight_action_blocked`
- observe-confirm wait reasons may pass through as `semantic_non_action_passthrough`

## Canonical Execution Block Reasons

- `opposite_position_lock`
- `clustered_entry_price_zone`
- `bb_buy_without_lower_touch`
- `bb_sell_without_upper_touch`
- `box_middle_buy_without_bb_support`
- `box_middle_sell_without_bb_resistance`
- `hard_guard_spread_too_wide`
- `hard_guard_volatility_too_low`
- `hard_guard_volatility_too_high`
