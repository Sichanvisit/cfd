# Re-Entry Contract

`re_entry_contract_v1` freezes canonical re-entry policy at the consumer boundary.

## Objective

Re-entry consumes current `observe_confirm_v2` handoff plus prior canonical entry ids and runtime cooldown state.
It does not reinterpret semantic layers.

## Core Rules

- same archetype confirm is required for re-entry
- re-entry cooldown is evaluated separately from archetype persistence
- middle averaging-in is forbidden
- immediate reverse entry after invalidation is forbidden in the same re-entry cycle

## Required Inputs

- current `observe_confirm_v2.state`
- current `observe_confirm_v2.action`
- current `observe_confirm_v2.side`
- current `observe_confirm_v2.archetype_id`
- current `observe_confirm_v2.invalidation_id`
- `prior_entry_archetype_id`
- `prior_entry_side`
- `prior_invalidation_id`
- `re_entry_cooldown_active`
- `box_state`
- `bb_state`

## Canonical Block Reasons

- `reentry_missing_prior_context`
- `reentry_same_archetype_confirm_required`
- `reentry_middle_averaging_forbidden`
- `reentry_immediate_reverse_after_invalidation_forbidden`
- `reentry_cooldown_active`

## Output Expectations

Resolver output keeps these dimensions separate:

- `same_archetype_confirmed`
- `persistence_ok`
- `cooldown_ok`
- `middle_reentry_forbidden`
- `reverse_after_invalidation_forbidden`
- `blocked_reason`

This separation lets execution timing policy evolve later without changing semantic identity rules.
