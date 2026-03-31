# Consumer Freeze / Handoff

`consumer_freeze_handoff_v1` freezes the final consumer handoff between Observe / Confirm output and downstream execution layers.

## Objective

Setup naming, entry guards, exit handoff, and re-entry policy should all run from a shared consumer handoff payload rooted in `ObserveConfirmSnapshot v2`.
Layer-mode policy should be read from `layer_mode_policy_v1` as the official policy input that sits above canonical observe-confirm identity.

## Completion Criteria

- consumer can operate from `ObserveConfirmSnapshot v2` plus non-semantic runtime support only
- setup, entry, exit, and re-entry responsibilities remain separated
- semantic layer reinterpretation is absent from consumer execution paths
- future `Layer Mode` can be added as a policy overlay above consumer handoff outputs

## Official Helper

- `resolve_consumer_handoff_payload(...)`

## Canonical Handoff Sections

- `observe_confirm_resolution`
- `observe_confirm`
- `layer_mode_policy_resolution`
- `layer_mode_policy`
- `setup_mapping_input`
- `setup_mapping`
- `exit_handoff`
- `re_entry_handoff`

## Principle

Consumer freeze is complete only when all downstream consumers can read canonical handoff outputs without pulling semantic vectors or detector internals back into execution logic.
Policy-strength control for those handoff outputs is frozen separately in `layer_mode_scope_contract_v1`, but the official consumer policy input is already `layer_mode_policy_v1`.
