# Setup Mapping Contract

`setup_mapping_contract_v1` freezes canonical `archetype_id -> setup_id` mapping inside `SetupDetector`.

## Canonical Base Mapping

- `upper_reject_sell -> range_upper_reversal_sell`
- `upper_break_buy -> breakout_retest_buy`
- `lower_hold_buy -> range_lower_reversal_buy`
- `lower_break_sell -> breakout_retest_sell`
- `mid_reclaim_buy -> range_lower_reversal_buy`
- `mid_lose_sell -> range_upper_reversal_sell`

## Allowed Specialization

- `mid_reclaim_buy` may specialize to `trend_pullback_buy`
- `mid_lose_sell` may specialize to `trend_pullback_sell`
- specialization may depend on `market_mode` or handoff `reason`
- specialization must stay inside the same archetype family

## Guardrail

- setup naming may refine `setup_id`
- setup naming may not rewrite `archetype_id`
- unmapped archetypes must be rejected instead of guessed
