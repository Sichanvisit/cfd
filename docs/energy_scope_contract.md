# Energy Scope Contract

`Energy` is redefined as a post-layer-mode helper, not a standalone semantic layer.

## Scope

- Read `evidence_vector_effective_v1`
- Read `belief_state_effective_v1`
- Read `barrier_state_effective_v1`
- Read `forecast_effective_policy_v1`
- Optionally read `observe_confirm_v2` action or side context
- Emit `energy_helper_v2`

## 13.0 Scope Freeze

- `Energy` is helper-only and post-layer-mode
- `Energy` is not a semantic layer
- `Energy` does not create semantic truth
- `Energy` does not create or mutate `archetype_id`
- `Energy` does not create or mutate `side`
- `Energy` does not create or mutate `invalidation_id`
- `Energy` does not create or mutate `management_profile_id`
- `selected_side` is utility-facing compression only, not semantic side ownership

## 13.1 Role Contract Freeze

- semantic layer answers: `what situation is happening`
- `Energy` answers: `how much the setup should be pushed or suppressed for action`
- `Energy` is a `utility/compression helper`
- `Energy` summarizes support, suppression, readiness, and wait bias
- `Energy` does not interpret the situation itself
- `Energy` does not own identity, archetype, side, invalidation, or management profile

## 13.2 Input Contract Freeze

- allowed required inputs:
- `evidence_vector_effective_v1`
- `belief_state_effective_v1`
- `barrier_state_effective_v1`
- `forecast_effective_policy_v1`
- allowed optional inputs:
- `observe_confirm_v2.action`
- `observe_confirm_v2.side`
- forbidden direct inputs include raw detector scores, legacy rule branches, raw PRS snapshots, and pre-effective semantic payloads
- `Energy` must ignore `observe_confirm_v2.state`, `archetype_id`, `invalidation_id`, and `management_profile_id`

## 13.3 Output Contract Freeze

- canonical output field is `energy_helper_v2`
- top-level output is exact and limited to:
- `selected_side`
- `action_readiness`
- `continuation_support`
- `reversal_support`
- `suppression_pressure`
- `forecast_support`
- `net_utility`
- `confidence_adjustment_hint`
- `soft_block_hint`
- `metadata`
- semantic label-like outputs are forbidden
- `metadata` is audit trace only and must not become a semantic label carrier

## 13.4 Composition Semantics Freeze

- `Evidence` means `setup strength support`
- `Belief` means `persistence/continuation bias`
- `Barrier` means `suppression/risk pressure`
- `Forecast` means `forward support or confirm-wait modulation`
- support family uses `+`
- suppression family uses `-`
- `Evidence`, `Belief`, and `Forecast` are support-side contributors
- `Barrier` is the suppression-side contributor
- `action_readiness` and `net_utility` are resolved as support minus suppression

## 13.5 Identity Non-Ownership Freeze

- `Energy` is not the identity owner
- canonical identity owner remains `observe_confirm_v2`
- `Energy` must not create or mutate `archetype_id`
- `Energy` must not create or mutate `side`
- `Energy` must not create or mutate `invalidation_id`
- `Energy` must not create or mutate `management_profile_id`
- `Energy` may use `observe_confirm_v2.action` and `observe_confirm_v2.side` as context only
- `selected_side` is not semantic identity side ownership

## 13.6 Consumer Usage Freeze

- `SetupDetector`: do not require `Energy`; optional reason annotation only
- `EntryService`: may read `action_readiness`, `confidence_adjustment_hint`, `soft_block_hint`, and `priority_hint` only
- `WaitEngine`: may read enter-versus-wait hints only
- `Exit`: may read advisory management hints only
- `ReEntry`: may read advisory management hints only
- no consumer may treat `Energy` as identity owner or semantic label source

## 13.7 Layer Mode Integration Freeze

- `Energy` reads `effective` outputs only
- `Energy` does not read raw semantic outputs
- `Energy` is a `post-layer-mode` bridge helper
- official order is `build_layer_mode_effective_metadata` then `build_energy_helper_v2`
- `Energy` sits above Layer Mode output, not below semantic computation
- `Energy` compresses the post-layer-mode world into utility-friendly helper values only

## 13.8 Utility Bridge Freeze

- `net_utility` stays as signed summary only
- do not place orders directly from `net_utility`
- do not block orders directly from `net_utility`
- canonical utility bridge is hint-first:
- `confidence_adjustment_hint`
- `soft_block_hint`
- `priority_hint`
- `wait_vs_enter_hint`
- consumers should route through intermediate hints before any live decision path

## 13.9 Migration / Dual-Write Freeze

- canonical runtime field is `energy_helper_v2`
- compatibility runtime field is `energy_snapshot`
- dual-write is required during migration:
- write new helper payload
- keep legacy snapshot alive as compatibility/transition path only
- consumer read preference stays canonical-helper-first
- replay must preserve both helper output and legacy bridge references
- live gate promotion is not allowed in this phase
- live gate behavior stays unchanged until a later explicit promotion step

## 13.10 Logging / Replay Freeze

- logging must preserve:
- `input_source_fields`
- `component_contributions`
- `support_vs_suppression_breakdown`
- `final_net_utility`
- `consumer_usage_trace`
- replay must be able to explain why a consumer chose `wait`, `soft block`, or confidence modulation
- consumer usage trace must record which helper fields were actually consumed
- consumer usage trace must say whether usage stayed advisory-only or touched a live gate
- `13.10` still keeps live gate unchanged; it only makes the explanation path replayable

## 13.11 Test Contract Freeze

- required regression axes are fixed:
- same semantic or effective input after Layer Mode must produce the same helper output
- larger `barrier` must increase `suppression_pressure`
- larger `evidence` or `belief` must increase `action_readiness`
- `forecast` may modulate forward support or confirm-wait bias, but it cannot change identity ownership
- `Energy` may not create or mutate `archetype_id`, `side`, `invalidation_id`, or `management_profile_id`
- replay must preserve raw semantic trace and effective helper source trace together
- migration must record `energy_helper_v2` and `energy_snapshot` together until a later promotion step changes that rule
- `13.11` freezes required regression coverage, not live threshold calibration

## 13.12 Freeze / Handoff

- completion means:
- `Energy` is no longer an independent meaning layer
- `Energy` sits above effective semantic outputs as a post-Layer-Mode helper
- consumer ownership is frozen as:
- identity -> `ObserveConfirm`
- policy -> `Layer Mode`
- utility hint -> `Energy`
- legacy `energy_snapshot` remains compatibility-only during transition
- after this freeze, `energy_engine` may be gradually absorbed into a `utility/decision helper` direction
- that future absorption must not restore semantic ownership back into `Energy`

## 14 Runtime Alignment Note

- canonical live helper remains `energy_helper_v2`
- legacy `energy_snapshot` remains compatibility-only and may be used only for replay or transition bridge reconstruction when canonical helper output is absent
- `EntryService` live usage is limited to `action_readiness`, `confidence_adjustment_hint`, `soft_block_hint`, and `priority_hint`
- `WaitEngine` live usage is limited to `wait_vs_enter_hint`, `action_readiness`, and `soft_block_hint` together with Layer Mode policy input
- `selected_side` remains utility-facing compression only and may not become semantic side ownership
- `net_utility` remains audit summary only and may not become a direct live order gate
- `consumer_usage_trace` must record only helper fields actually consumed by the live branch

## Non-Goals

- Do not create semantic truth
- Do not rewrite `archetype_id`
- Do not rewrite `side`
- Do not rewrite `invalidation_id`
- Do not rewrite `management_profile_id`

## Output Shape

- `selected_side`
- `action_readiness`
- `continuation_support`
- `reversal_support`
- `suppression_pressure`
- `forecast_support`
- `net_utility`
- `confidence_adjustment_hint`
- `soft_block_hint`
- `metadata`

## Migration

- `energy_helper_v2` is canonical
- `energy_snapshot` stays compatibility-only during migration
- replay and logging must preserve both helper output and legacy bridge references
- live gate behavior remains unchanged in `13.9`
