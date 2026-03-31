# Observe / Confirm / Action Management Profile Taxonomy

`observe_confirm_management_profile_taxonomy_v2` freezes canonical post-entry management identities for each trade archetype.

## Canonical Mapping

- `upper_reject_sell -> reversal_profile`
- `upper_break_buy -> breakout_hold_profile`
- `lower_hold_buy -> support_hold_profile`
- `lower_break_sell -> breakdown_hold_profile`
- `mid_reclaim_buy -> mid_reclaim_fast_exit_profile`
- `mid_lose_sell -> mid_lose_fast_exit_profile`

## Principles

- `management_profile_id` is canonical contract data, not setup name and not archetype id
- `management_profile_id` is the official consumer and exit handoff field
- the same `archetype_id` should carry the same `management_profile_id` across observe and confirm states
- empty `management_profile_id` is allowed only when `archetype_id` is empty

## Consumer Note

Later `Consumer`, `Exit`, and `Re-entry` logic should bind behavior from `management_profile_id` rather than re-parsing `reason` or duplicating archetype-specific management rules.
