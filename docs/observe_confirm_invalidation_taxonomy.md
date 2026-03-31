# Observe / Confirm / Action Invalidation Taxonomy

`observe_confirm_invalidation_taxonomy_v2` freezes canonical failure identities for each trade archetype.

## Canonical Mapping

- `upper_reject_sell -> upper_break_reclaim`
- `upper_break_buy -> breakout_failure`
- `lower_hold_buy -> lower_support_fail`
- `lower_break_sell -> breakdown_failure`
- `mid_reclaim_buy -> mid_relose`
- `mid_lose_sell -> mid_reclaim`

## Principles

- `invalidation_id` is canonical contract data, not free-text reason
- the same `archetype_id` should carry the same `invalidation_id` across observe and confirm states
- empty `invalidation_id` is allowed only when `archetype_id` is empty
- consumers should bind failure logic from `invalidation_id`, not by parsing `reason`

## Consumer Note

`SetupDetector`, `EntryService`, and later `Exit` logic may use `invalidation_id` as the stable failure handle, but they must not redefine the taxonomy.
