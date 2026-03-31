# Observe / Confirm / Action Scope Freeze

`observe_confirm_scope_v1` freezes the responsibility boundary for the Observe / Confirm / Action layer.

## Objective

This layer decides only whether the current semantic state should be treated as observe, confirm, or no-trade for a candidate trade archetype.

## In Scope

- determine whether the semantic state is observe, confirm, or no-trade
- emit routing output through `observe_confirm_v2` with `observe_confirm_v1` compatibility dual-write
- carry semantic reason and routing metadata needed by downstream consumers
- dual-write `observe_confirm_v1` and `observe_confirm_v2` during migration

## Out of Scope

- setup naming
- entry guard or execution gating
- exit rule selection
- re-entry authorization
- order send, lot sizing, or broker execution

## Consumer Boundary

- `SetupDetector`: names or maps a confirmed archetype only
- `EntryService`: applies execution guards only
- `Exit`: binds management behavior later from the entry archetype and profile
- `Re-entry`: may require same-archetype confirmation later, but is not authorized here

## Runtime Ownership Alignment

- canonical identity owner is `observe_confirm_v2`
- runtime routing no longer depends on legacy `energy_snapshot`
- confirm versus wait routing is derived from semantic bundle inputs plus forecast modulation only
- `forecast` may modulate confidence or action timing, but it may not override `archetype_id`, `side`, `invalidation_id`, or `management_profile_id`
- internal routing must not reintroduce `buy_force`, `sell_force`, or `net_force` as identity-ownership inputs

## Migration Boundary

- `observe_confirm_v1` remains compatibility dual-write only
- consumers must resolve observe-confirm handoff through canonical-first `v2 -> v1` fallback
- compatibility fallback is allowed only when canonical `observe_confirm_v2` is absent
- compatibility payloads may support migration and replay, but they may not regain identity ownership

## Completed Definitions

- `scope_freeze_v1`
- `input_contract_v2`
- `output_contract_v2`
- `state_semantics_v2`
- `archetype_taxonomy_v2`
- `invalidation_taxonomy_v2`
- `management_profile_taxonomy_v2`
- `routing_policy_v2`
- `confidence_semantics_v2`
- `migration_dual_write_v1`
- `action_side_semantics_v2`
- `test_contract_v1`
- `freeze_handoff_v1`

## Deferred Definitions

The following are intentionally deferred to later `10A` steps:

None.
