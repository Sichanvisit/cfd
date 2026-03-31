# Consumer Scope Freeze

`consumer_scope_v1` freezes the Observe / Confirm consumer boundary.

## Objective

Consumer layers read canonical `observe_confirm_v2` handoff data and connect it to setup naming, entry guards, exit handoff, and re-entry policy hooks.

Input details are frozen separately in `consumer_input_contract_v1`.
Layer-mode policy input is frozen separately in `consumer_layer_mode_integration_v1`.
`SetupDetector` naming responsibility is frozen separately in `setup_detector_responsibility_v1`.
Archetype-to-setup rules are frozen separately in `setup_mapping_contract_v1`.
Entry guard reasons are frozen separately in `entry_guard_contract_v1`.
`EntryService` execution boundary is frozen separately in `entry_service_responsibility_v1`.
Exit handoff is frozen separately in `exit_handoff_contract_v1`.
Re-entry policy is frozen separately in `re_entry_contract_v1`.
Consumer audit logging is frozen separately in `consumer_logging_contract_v1`.
Consumer migration behavior is frozen separately in `consumer_migration_freeze_v1`.
Consumer regression locking is frozen separately in `consumer_test_contract_v1`.
Consumer freeze and downstream handoff are frozen separately in `consumer_freeze_handoff_v1`.

## In Scope

- read `state`, `action`, `side`, `confidence`, `reason`, `archetype_id`, `invalidation_id`, `management_profile_id`
- read `layer_mode_policy_v1` as the official policy overlay input above canonical observe-confirm identity
- read `energy_helper_v2` only through the frozen component usage boundary
- map canonical handoff into `SetupDetector`
- apply execution guards in `EntryService`
- compare enter versus wait in `WaitEngine` with helper-only energy hints
- pass `management_profile_id` and `invalidation_id` into later exit and re-entry flows
- require same-archetype re-confirmation before re-entry
- keep re-entry cooldown separate from archetype persistence
- record consumer pass or block decisions with canonical handoff ids
- read observe-confirm through one shared resolver with `v2 -> v1` fallback only

## Energy Usage

- `SetupDetector` does not require `energy_helper_v2`; optional reason annotation only
- `EntryService` may read readiness, priority, confidence hint, and soft block hint only
- `WaitEngine` may read enter-versus-wait hints only
- `Exit` may read advisory management hints only
- `ReEntry` may read advisory management hints only
- no consumer may place, block, or rank live orders directly from `net_utility`
- no consumer may promote `energy_helper_v2` into an identity source

## Current Runtime Ownership

- `EntryService` reads identity from canonical `observe_confirm_v2`, or from `observe_confirm_v1` only when canonical handoff is absent through the shared migration resolver
- `EntryService` reads policy from `layer_mode_policy_v1`
- `EntryService` reads utility hints from `energy_helper_v2` through `action_readiness`, `confidence_adjustment_hint`, `soft_block_hint`, and `priority_hint` only
- `WaitEngine` reads `layer_mode_policy_v1` together with `energy_helper_v2.wait_vs_enter_hint`, `action_readiness`, and `soft_block_hint` for live enter-versus-wait comparison
- `SetupDetector` still does not require `Energy` beyond optional annotation
- `Exit` and `ReEntry` remain advisory-only consumers of management hints
- `selected_side` may not be promoted into semantic side ownership
- `net_utility` may not become a direct place/block/rank live-order gate
- consumer logging must record only the helper fields actually consumed by the live branch

## Out of Scope

- semantic layer reinterpretation
- raw detector direct read
- semantic vector recomputation
- archetype identity rewriting
- energy helper identity promotion
- middle averaging-in policy redefinition outside `re_entry_contract_v1`
