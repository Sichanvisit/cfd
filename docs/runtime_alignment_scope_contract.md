# Runtime Alignment Scope Contract

`14.0 Scope Freeze` closes the scope of the runtime-alignment phase before any identity or consumer wiring changes are made.

## Objective

Align runtime behavior with the documented `Position -> Energy` ownership model without introducing a new semantic layer.

## Priority Order

1. `identity ownership`
2. `live consumer wiring`
3. `truthful logging`

## In Scope

- detach legacy `energy_snapshot` from `ObserveConfirm` identity ownership
- make live consumer decisions read `ObserveConfirm` identity, `Layer Mode` policy, and `Energy` helper hints together
- record only actual `Energy` helper consumption in replay and audit logs
- re-freeze the docs after runtime behavior matches the documented ownership split

## Out of Scope

- creating a new meaning layer
- redefining semantic foundation meaning
- promoting `net_utility` into a direct order gate
- removing compatibility bridges before runtime alignment is proven

## Frozen Invariants

- `ObserveConfirm` remains the canonical identity owner
- `Layer Mode` remains the policy overlay above raw semantic outputs
- `Energy` remains a post-layer-mode helper only

## Implementation Sequence

- `14.0 Scope Freeze`
- `14.1 ObserveConfirm Legacy Energy Detach`
- `14.2 ObserveConfirm Semantic Routing Hardening`
- `14.3 EntryService Consumer Stack Activation`
- `14.4 WaitEngine Hint Activation`
- `14.5 Truthful Consumer Usage Logging`
- `14.6 Compatibility / Migration Guard`
- `14.7 Test Hardening`
- `14.8 Docs / Handoff Re-freeze`

## Current Completion

Completed in code:

- `14.0 Scope Freeze`
- `14.1 ObserveConfirm Legacy Energy Detach`
- `14.2 ObserveConfirm Semantic Routing Hardening`
- `14.3 EntryService Consumer Stack Activation`
- `14.4 WaitEngine Hint Activation`
- `14.5 Truthful Consumer Usage Logging`
- `14.6 Compatibility / Migration Guard`
- `14.7 Test Hardening`
- `14.8 Docs / Handoff Re-freeze`

Still deferred:

- None.

## 14.6 Guard Meaning

`observe_confirm_v1` and `energy_snapshot` may remain present during migration, but they are now restricted to compatibility-only bridge roles.

- `observe_confirm_v1` may be used only when canonical `observe_confirm_v2` is absent
- `energy_snapshot` may be used only when canonical `energy_helper_v2` is absent and helper replay reconstruction is needed
- neither legacy field may regain identity ownership
- neither legacy field may become a new direct live gate source

## 14.7 Test Axes

The runtime-alignment phase now locks these regression axes in tests:

- changing `energy_snapshot` may not mutate `observe_confirm_v2` identity ownership
- changing `layer_mode_policy_v1` may change consumer execution decisions, but not canonical handoff ids
- changing `energy_helper_v2` may change priority, wait, or soft-block behavior, but not canonical handoff ids
- `consumer_usage_trace.consumed_fields` must match actual helper fields used by the live branch
- `WaitEngine` must reflect `wait_vs_enter_hint` in real valuation and decision paths
- `EntryService` must reflect `soft_block_hint` and `priority_hint` in live execution outcomes

## 14.8 Docs / Handoff Re-freeze

The runtime-alignment docs are now re-frozen to the current live ownership split.

- `ObserveConfirm` owns identity without legacy `energy_snapshot`
- `Consumer` live decisions read `ObserveConfirm` identity, `Layer Mode` policy, and `Energy` helper hints together
- `observe_confirm_v1` and `energy_snapshot` remain compatibility-only bridges
- replay and audit logs must describe only actual helper usage
