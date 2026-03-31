# Observe / Confirm / Action Archetype Taxonomy

`observe_confirm_archetype_taxonomy_v2` freezes canonical trade archetypes as entry identities.

## Core Set

- `upper_reject_sell`
- `upper_break_buy`
- `lower_hold_buy`
- `lower_break_sell`
- `mid_reclaim_buy`
- `mid_lose_sell`

## Principles

- `archetype_id` is entry identity
- `archetype_id` is not lifecycle state
- `archetype_id` is not setup name
- observe and confirm may carry the same `archetype_id`
- neutral or unresolved observe states may emit empty `archetype_id`

## Consumer Note

`SetupDetector` may still specialize these canonical archetypes into setup names using market mode, reason, and surrounding context.
