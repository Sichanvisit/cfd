# Layer Mode Scope Freeze

`layer_mode_scope_v1` freezes Layer Mode as an always-compute policy overlay.
Canonical mode values are frozen separately in `layer_mode_contract_v1`.
Mode-addressable semantic layers are frozen separately in `layer_mode_layer_inventory_v1`.
Default rollout policy is frozen separately in `layer_mode_default_policy_v1`.
Raw/effective dual-write is frozen separately in `layer_mode_dual_write_v1`.
Execution influence semantics are frozen separately in `layer_mode_influence_semantics_v1`.
Layer-by-layer application policy is frozen separately in `layer_mode_application_contract_v1`.
Identity guard is frozen separately in `layer_mode_identity_guard_v1`.
Canonical policy-applied output is frozen separately in `layer_mode_policy_overlay_output_v1`.
Replayable logging output is frozen separately in `layer_mode_logging_replay_contract_v1`.
Regression behavior lock is frozen separately in `layer_mode_test_contract_v1`.
Final handoff boundary is frozen separately in `layer_mode_freeze_handoff_v1`.

## Objective

Layer Mode does not turn semantic layers on or off. Raw semantic outputs are always computed, and later mode policy only changes effective outputs or execution influence.

## In Scope

- preserve raw outputs for `Position`, `Response`, `State`, `Evidence`, `Belief`, `Barrier`, and `Forecast`
- keep Layer Mode above consumer handoff and below execution
- reserve effective-output shaping for later mode definitions
- keep raw outputs available even after future policy overlays are added

## Out of Scope

- disabling semantic computation
- redefining semantic meaning
- rewriting `ObserveConfirmSnapshot` identity fields
- re-introducing semantic reinterpretation inside consumer execution paths

## Principle

`raw` is always present.
`effective` is always emitted beside `raw`, even if the current bridge still equals the raw output.
Layer Mode exists to control influence strength, not semantic existence.
Which influence types are allowed for each layer is frozen separately from the mode vocabulary itself.
Which role each layer actually plays in rollout is also frozen separately from the influence matrix.
Identity protection for `Belief / Barrier / Forecast` is also frozen separately from rollout mode.
Policy-applied output is emitted separately from raw semantic outputs and may remain bridge-only until runtime deltas are introduced.
Logging and replay payloads must remain rich enough to audit `shadow -> assist -> enforce` migration later.

## Current Runtime Ownership

- Layer Mode emits raw semantic outputs, effective semantic outputs, and `layer_mode_policy_v1` together
- `layer_mode_policy_v1` is the official policy input for live consumers
- Layer Mode may hard-block, suppress, or assist execution influence
- Layer Mode may not rewrite `ObserveConfirm` identity fields
- `Energy` reads Layer Mode effective outputs after policy application
- consumers may read Layer Mode policy for execution decisions, but they may not treat Layer Mode as a new semantic owner
